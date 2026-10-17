// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later

import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import Meta from 'gi://Meta';
import Soup from 'gi://Soup?version=3.0';
import St from 'gi://St';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as MessageTray from 'resource:///org/gnome/shell/ui/messageTray.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

import {fetchWallpaper, pixbufFromBytes, wallpaperUrl} from './lib/server.js';
import {compose, colorToHex} from './lib/compose.js';

Gio._promisify(Gio.File.prototype, 'load_contents_async');
Gio._promisify(Gio.File.prototype, 'replace_contents_bytes_async', 'replace_contents_finish');
Gio._promisify(Gio.File.prototype, 'make_directory_async');
Gio._promisify(Gio.File.prototype, 'delete_async');

const STARTUP_DELAY_SECONDS = 5;
const MUTTER_EXPERIMENTAL = 'experimental-features';
const ICON_NAME = 'preferences-desktop-wallpaper-symbolic';

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
            // The label is drawn by the server in the language asked: both change the image
            this._settings.connect('changed::language', () => this._schedule(true)),
            this._settings.connect('changed::show-label', () => this._schedule(true)),
            this._settings.connect('changed::background', () => this._scheduleCompose()),
            this._settings.connect('changed::background-color', () => this._scheduleCompose()),
            this._settings.connect('changed::check-interval', () => this._startTimer()),
            this._settings.connect('changed::panel-indicator', () => this._syncIndicator()),
            this._settings.connect('changed::reason', () => this._updateIndicator()),
            this._settings.connect('changed::title', () => this._updateIndicator()),
            this._settings.connect('changed::author', () => this._updateIndicator()),
        ];
        this._syncIndicator();
        this._monitorsId = Main.layoutManager.connect('monitors-changed', () => this._scheduleCompose());
        this._workAreasId = global.display.connect('workareas-changed', () => this._scheduleCompose());

        this._startupId = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, STARTUP_DELAY_SECONDS, () => {
            this._startupId = 0;
            this._schedule(false, true);
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
            this._schedule(false, true);
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
        this._destroyIndicator();
        this._source?.destroy();
        this._source = null;
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

    /** automatic: a periodic check, which also ends a day chosen with "Use as wallpaper". */
    _schedule(force, automatic = false) {
        this._enqueue(cancellable => this._update(force, automatic, cancellable));
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

    async _update(force, automatic, cancellable) {
        if (automatic && this._settings.get_string('show-date') !== '') {
            // Back to today's image
            this._settings.set_string('show-date', '');
            force = true;
        }
        let result;
        try {
            result = await fetchWallpaper(this._session, wallpaperUrl(this._settings), cancellable);
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

        // A new image found by a periodic check (not the first one, nor a change by hand)
        const previousHash = this._settings.get_string('image-hash');
        const isNew = automatic && previousHash !== '' && hash !== previousHash;

        await this._ensureDirectory(this._originalFile.get_parent(), cancellable);
        await this._originalFile.replace_contents_bytes_async(result.bytes, null, false,
            Gio.FileCreateFlags.REPLACE_DESTINATION, cancellable);

        this._pixbuf = result.pixbuf;
        this._settings.set_string('title', result.titleWithYear);
        this._settings.set_string('author', result.author);
        this._settings.set_string('reason', result.reason);
        this._settings.set_string('image-hash', hash);
        await this._composeAndSet(cancellable);
        this._setStatus('The wallpaper has been updated.');
        if (isNew)
            this._notify(result);
    }

    // ------------------------------------------------------------------ top bar

    /** The icon in the top bar exists only while the option is on. */
    _syncIndicator() {
        const wanted = this._settings.get_boolean('panel-indicator');
        if (wanted && !this._indicator)
            this._createIndicator();
        else if (!wanted)
            this._destroyIndicator();
    }

    _createIndicator() {
        const button = new PanelMenu.Button(0.0, this.metadata.name, false);
        button.add_child(new St.Icon({icon_name: ICON_NAME, style_class: 'system-status-icon'}));

        // The data of the current image, then the actions
        this._reasonItem = new PopupMenu.PopupMenuItem('', {reactive: false});
        this._titleItem = new PopupMenu.PopupMenuItem('', {reactive: false});
        this._authorItem = new PopupMenu.PopupMenuItem('', {reactive: false});
        this._reasonItem.label.style = 'font-weight: bold;';
        for (const item of [this._reasonItem, this._titleItem, this._authorItem])
            button.menu.addMenuItem(item);
        button.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        button.menu.addAction('Image of the Day\u2026', () => this.openPreferences());
        button.menu.addAction('Refresh Wallpaper', () => this._schedule(true));

        Main.panel.addToStatusArea(this.uuid, button);
        this._indicator = button;
        this._updateIndicator();
    }

    _updateIndicator() {
        if (!this._indicator)
            return;
        const texts = [
            [this._reasonItem, this._settings.get_string('reason')],
            [this._titleItem, this._settings.get_string('title') || 'Catholic Background of the Day'],
            [this._authorItem, this._settings.get_string('author')],
        ];
        for (const [item, text] of texts) {
            item.label.text = text;
            item.visible = text !== '';
        }
    }

    _destroyIndicator() {
        this._indicator?.destroy();
        this._indicator = this._reasonItem = this._titleItem = this._authorItem = null;
    }

    /** Notification of a new image (only with the icon in the top bar); clicking it opens the preferences. */
    _notify(result) {
        if (!this._settings.get_boolean('panel-indicator'))
            return;
        if (!this._source) {
            this._source = new MessageTray.Source({title: this.metadata.name, iconName: ICON_NAME});
            this._source.connect('destroy', () => {
                this._source = null;
            });
            Main.messageTray.add(this._source);
        }
        const body = [result.titleWithYear, result.author].filter(t => t).join(' \u2014 ');
        const notification = new MessageTray.Notification({
            source: this._source,
            title: result.reason || 'New image of the day',
            body: body || 'The wallpaper has changed.',
        });
        notification.connect('activated', () => this.openPreferences());
        this._source.addNotification(notification);
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
