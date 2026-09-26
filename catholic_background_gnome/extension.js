// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later

import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import Meta from 'gi://Meta';
import Soup from 'gi://Soup?version=3.0';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

import {fetchWallpaper, pixbufFromBytes} from './lib/server.js';
import {compose, colorToHex} from './lib/compose.js';

Gio._promisify(Gio.File.prototype, 'load_contents_async');
Gio._promisify(Gio.File.prototype, 'replace_contents_bytes_async', 'replace_contents_finish');
Gio._promisify(Gio.File.prototype, 'make_directory_async');
Gio._promisify(Gio.File.prototype, 'delete_async');

const STARTUP_DELAY_SECONDS = 5;
const MUTTER_EXPERIMENTAL = 'experimental-features';

export default class CatholicBackgroundExtension extends Extension {
    enable() {
        this._settings = this.getSettings();
        this._background = new Gio.Settings({schema_id: 'org.gnome.desktop.background'});
        this._session = new Soup.Session({timeout: 60});
        this._cancellable = new Gio.Cancellable();
        this._queue = Promise.resolve();
        this._pixbuf = null;  // original image of today, once loaded

        const dataDir = GLib.build_filenamev([GLib.get_user_data_dir(), 'backgrounds', 'catholic-background']);
        this._dataDir = Gio.File.new_for_path(dataDir);
        this._originalFile = Gio.File.new_for_path(GLib.build_filenamev([GLib.get_user_cache_dir(), 'catholic-background', 'original']));

        this._settingsIds = [
            this._settings.connect('changed::server-url', () => this._schedule(true)),
            this._settings.connect('changed::refresh-request', () => this._schedule(true)),
            this._settings.connect('changed::background', () => this._scheduleCompose()),
            this._settings.connect('changed::background-color', () => this._scheduleCompose()),
            this._settings.connect('changed::check-interval', () => this._startTimer()),
        ];
        this._monitorsId = Main.layoutManager.connect('monitors-changed', () => this._scheduleCompose());
        this._workAreasId = global.display.connect('workareas-changed', () => this._scheduleCompose());

        this._startupId = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, STARTUP_DELAY_SECONDS, () => {
            this._startupId = 0;
            this._schedule(false);
            return GLib.SOURCE_REMOVE;
        });
        this._startTimer();
    }

    /** Checks the server every check-interval minutes (the server may have several images a day). */
    _startTimer() {
        if (this._timerId)
            GLib.source_remove(this._timerId);
        const minutes = this._settings.get_uint('check-interval');
        this._timerId = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, minutes * 60, () => {
            this._schedule(false);
            return GLib.SOURCE_CONTINUE;
        });
    }

    disable() {
        // The wallpaper is left as it is: disable() is also called when the
        // screen is locked, and the image must not change then.
        this._cancellable.cancel();
        for (const id of [this._startupId, this._timerId, this._composeId]) {
            if (id)
                GLib.source_remove(id);
        }
        this._startupId = this._timerId = this._composeId = 0;
        for (const id of this._settingsIds)
            this._settings.disconnect(id);
        Main.layoutManager.disconnect(this._monitorsId);
        global.display.disconnect(this._workAreasId);
        this._session.abort();

        this._settingsIds = [];
        this._settings = null;
        this._background = null;
        this._session = null;
        this._cancellable = null;
        this._queue = null;
        this._pixbuf = null;
        this._dataDir = null;
        this._originalFile = null;
    }

    /** Runs jobs one after another; they stop if the extension is disabled meanwhile. */
    _enqueue(job) {
        const cancellable = this._cancellable;
        this._queue = this._queue.then(() => {
            if (!cancellable.is_cancelled())
                return job(cancellable);
            return undefined;
        }).catch(e => {
            if (!e.matches?.(Gio.IOErrorEnum, Gio.IOErrorEnum.CANCELLED))
                console.warn(`Catholic background: ${e.message}`);
        });
    }

    _schedule(force) {
        this._enqueue(cancellable => this._update(force, cancellable));
    }

    /** Recompose soon (several monitor/work area signals usually arrive together). */
    _scheduleCompose() {
        if (this._composeId)
            GLib.source_remove(this._composeId);
        this._composeId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 500, () => {
            this._composeId = 0;
            this._enqueue(cancellable => this._composeAndSet(cancellable));
            return GLib.SOURCE_REMOVE;
        });
    }

    async _update(force, cancellable) {
        let result;
        try {
            result = await fetchWallpaper(this._session, this._settings.get_string('server-url'), cancellable);
        } catch (e) {
            if (e.matches?.(Gio.IOErrorEnum, Gio.IOErrorEnum.CANCELLED))
                throw e;
            // Keep the current wallpaper; the next check will try again
            this._setStatus(`${e.message}. The current wallpaper has been kept.`);
            return;
        }

        // Change the wallpaper only when the server has a different image
        const hash = GLib.compute_checksum_for_bytes(GLib.ChecksumType.SHA1, result.bytes);
        if (!force && hash === this._settings.get_string('image-hash') && this._currentFileExists()) {
            this._setStatus('The image has not changed.');
            return;
        }

        await this._ensureDirectory(this._originalFile.get_parent(), cancellable);
        await this._originalFile.replace_contents_bytes_async(result.bytes, null, false,
            Gio.FileCreateFlags.REPLACE_DESTINATION, cancellable);

        this._pixbuf = result.pixbuf;
        this._settings.set_string('title', result.title);
        this._settings.set_string('author', result.author);
        this._settings.set_string('image-hash', hash);
        await this._composeAndSet(cancellable);
        this._setStatus('The wallpaper has been updated.');
    }

    _setStatus(message) {
        const time = GLib.DateTime.new_now_local().format('%H:%M');
        this._settings.set_string('status', `Last check at ${time}: ${message}`);
    }

    _currentFileExists() {
        const path = this._settings.get_string('current-file');
        return path !== '' && GLib.file_test(path, GLib.FileTest.EXISTS);
    }

    /** Screen size in pixels and the area not covered by panels, for the primary monitor. */
    _screenGeometry() {
        const layout = Main.layoutManager;
        const monitor = layout.primaryMonitor;
        const workArea = layout.getWorkAreaForMonitor(layout.primaryIndex);

        // With fractional scaling (logical layout) sizes are in logical
        // pixels; otherwise they are already physical pixels.
        const mutter = new Gio.Settings({schema_id: 'org.gnome.mutter'});
        // (GNOME 50 and later are always Wayland compositors)
        const wayland = Meta.is_wayland_compositor?.() ?? true;
        const logical = wayland &&
            mutter.get_strv(MUTTER_EXPERIMENTAL).includes('scale-monitor-framebuffer');
        const k = logical ? monitor.geometry_scale : 1;

        return {
            screen: {width: Math.round(monitor.width * k), height: Math.round(monitor.height * k)},
            free: {
                x: Math.round((workArea.x - monitor.x) * k),
                y: Math.round((workArea.y - monitor.y) * k),
                width: Math.round(workArea.width * k),
                height: Math.round(workArea.height * k),
            },
        };
    }

    async _composeAndSet(cancellable) {
        if (!this._pixbuf) {
            if (!this._originalFile.query_exists(null))
                return;
            const [contents] = await this._originalFile.load_contents_async(cancellable);
            this._pixbuf = pixbufFromBytes(new GLib.Bytes(contents));
        }

        const {screen, free} = this._screenGeometry();
        const {pixbuf, fillColor} = compose(this._pixbuf, screen, free,
            this._settings.get_string('background'), this._settings.get_string('background-color'));
        const [, jpeg] = pixbuf.save_to_bufferv('jpeg', ['quality'], ['92']);

        // A new file name every time, so that GNOME notices the change
        await this._ensureDirectory(this._dataDir, cancellable);
        const file = this._dataDir.get_child(`${GLib.DateTime.new_now_utc().to_unix_usec()}.jpg`);
        await file.replace_contents_bytes_async(new GLib.Bytes(jpeg), null, false,
            Gio.FileCreateFlags.REPLACE_DESTINATION, cancellable);

        const previous = this._settings.get_string('current-file');
        const uri = file.get_uri();
        this._background.set_string('picture-options', 'scaled');
        this._background.set_string('primary-color', colorToHex(fillColor));
        this._background.set_string('color-shading-type', 'solid');
        this._background.set_string('picture-uri', uri);
        this._background.set_string('picture-uri-dark', uri);
        this._settings.set_string('current-file', file.get_path());

        if (previous && previous !== file.get_path()) {
            try {
                await Gio.File.new_for_path(previous).delete_async(GLib.PRIORITY_DEFAULT, cancellable);
            } catch (e) {
                // It may have been deleted already
            }
        }
    }

    async _ensureDirectory(dir, cancellable) {
        if (dir.query_exists(null))
            return;
        const parent = dir.get_parent();
        if (parent && !parent.query_exists(null))
            await this._ensureDirectory(parent, cancellable);
        try {
            await dir.make_directory_async(GLib.PRIORITY_DEFAULT, cancellable);
        } catch (e) {
            if (!e.matches?.(Gio.IOErrorEnum, Gio.IOErrorEnum.EXISTS))
                throw e;
        }
    }
}
