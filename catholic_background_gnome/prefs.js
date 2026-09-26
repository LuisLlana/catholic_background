// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later

import Adw from 'gi://Adw';
import Gdk from 'gi://Gdk';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Gtk from 'gi://Gtk';
import Soup from 'gi://Soup?version=3.0';

import {ExtensionPreferences} from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';

import {fetchWallpaper, urlForTimestamp} from './lib/server.js';

function hexToRgba(hex) {
    const rgba = new Gdk.RGBA();
    if (!rgba.parse(hex))
        rgba.parse('#000000');
    return rgba;
}

function rgbaToHex(rgba) {
    return `#${[rgba.red, rgba.green, rgba.blue]
        .map(v => Math.round(v * 255).toString(16).padStart(2, '0')).join('')}`;
}

export default class CatholicBackgroundPreferences extends ExtensionPreferences {
    fillPreferencesWindow(window) {
        const settings = this.getSettings();
        const session = new Soup.Session({timeout: 60});
        window._settings = settings;
        window.set_default_size(600, 820);

        const toast = title => window.add_toast(new Adw.Toast({title, timeout: 5}));

        const page = new Adw.PreferencesPage({
            title: 'General',
            icon_name: 'preferences-desktop-wallpaper-symbolic',
        });
        window.add(page);

        // ---------- Today's image ----------
        const today = new Adw.PreferencesGroup({title: 'Today\u2019s Image'});
        page.add(today);

        const refreshButton = new Gtk.Button({
            icon_name: 'view-refresh-symbolic',
            tooltip_text: 'Download the image again',
            valign: Gtk.Align.CENTER,
            css_classes: ['flat'],
        });
        refreshButton.connect('clicked', () => {
            settings.set_int64('refresh-request', GLib.get_real_time());
            toast('Downloading today\u2019s image\u2026');
        });
        today.set_header_suffix(refreshButton);

        const picture = new Gtk.Picture({
            content_fit: Gtk.ContentFit.CONTAIN,
            can_shrink: true,
            height_request: 240,
        });
        const placeholder = new Adw.StatusPage({
            icon_name: 'preferences-desktop-wallpaper-symbolic',
            title: 'No Image Yet',
            description: 'Make sure the extension is enabled and the server is reachable.',
            css_classes: ['compact'],
            height_request: 240,
        });
        const stack = new Gtk.Stack({css_classes: ['card'], overflow: Gtk.Overflow.HIDDEN});
        stack.add_named(picture, 'picture');
        stack.add_named(placeholder, 'placeholder');
        today.add(stack);

        // Separate group so that the rows appear below the preview
        const details = new Adw.PreferencesGroup();
        page.add(details);
        const titleRow = new Adw.ActionRow({title: 'Title', css_classes: ['property'], subtitle_selectable: true});
        const authorRow = new Adw.ActionRow({title: 'Author', css_classes: ['property'], subtitle_selectable: true});
        const statusRow = new Adw.ActionRow({title: 'Last check', css_classes: ['property']});
        details.add(titleRow);
        details.add(authorRow);
        details.add(statusRow);

        const updateToday = () => {
            const path = settings.get_string('current-file');
            if (path && GLib.file_test(path, GLib.FileTest.EXISTS)) {
                picture.set_filename(path);
                stack.visible_child_name = 'picture';
            } else {
                picture.set_filename(null);
                stack.visible_child_name = 'placeholder';
            }
            titleRow.subtitle = GLib.markup_escape_text(settings.get_string('title') || '\u2014', -1);
            authorRow.subtitle = GLib.markup_escape_text(settings.get_string('author') || '\u2014', -1);
            statusRow.subtitle = GLib.markup_escape_text(settings.get_string('status') || '\u2014', -1);
        };
        updateToday();

        // ---------- Server ----------
        const server = new Adw.PreferencesGroup({title: 'Server'});
        page.add(server);

        const urlRow = new Adw.EntryRow({
            title: 'Server URL',
            text: settings.get_string('server-url'),
            show_apply_button: true,
            input_purpose: Gtk.InputPurpose.URL,
        });
        urlRow.connect('apply', () => {
            const url = urlRow.text.trim();
            try {
                urlForTimestamp(url, 0);
            } catch (e) {
                toast(e.message);
                return;
            }
            settings.set_string('server-url', url);
            toast('Server saved. Downloading today\u2019s image\u2026');
        });

        const testButton = new Gtk.Button({
            label: 'Test',
            tooltip_text: 'Check the server without changing the wallpaper',
            valign: Gtk.Align.CENTER,
        });
        testButton.connect('clicked', async () => {
            testButton.sensitive = false;
            try {
                const result = await fetchWallpaper(session, urlRow.text, null);
                const what = [result.title || 'an image without title', result.author].filter(Boolean).join(', ');
                toast(`Connection OK: ${what} (${result.pixbuf.get_width()}\u00d7${result.pixbuf.get_height()})`);
            } catch (e) {
                toast(e.message);
            } finally {
                testButton.sensitive = true;
            }
        });
        urlRow.add_suffix(testButton);

        const resetButton = new Gtk.Button({
            icon_name: 'edit-undo-symbolic',
            tooltip_text: 'Restore the default server',
            valign: Gtk.Align.CENTER,
            css_classes: ['flat'],
        });
        resetButton.connect('clicked', () => settings.reset('server-url'));
        urlRow.add_suffix(resetButton);
        server.add(urlRow);

        const intervalRow = new Adw.SpinRow({
            title: 'Check every',
            subtitle: 'Minutes. The wallpaper changes only when the server has a different image.',
            adjustment: new Gtk.Adjustment({lower: 5, upper: 1440, step_increment: 5, page_increment: 60}),
        });
        settings.bind('check-interval', intervalRow, 'value', Gio.SettingsBindFlags.DEFAULT);
        server.add(intervalRow);

        // ---------- Around the image ----------
        const around = new Adw.PreferencesGroup({
            title: 'Around the Image',
            description: 'The image is always shown complete and as big as possible. Choose how to fill the rest of the screen.',
        });
        page.add(around);

        const checks = {};
        let firstCheck = null;
        const options = [
            ['blur', 'Blurred image', 'The image enlarged and blurred'],
            ['average', 'Average color', 'The average color of the image'],
            ['color', 'Color', 'A color of your choice'],
        ];
        let colorRow = null;
        for (const [value, title, subtitle] of options) {
            const check = new Gtk.CheckButton({valign: Gtk.Align.CENTER, group: firstCheck});
            firstCheck ??= check;
            const row = new Adw.ActionRow({title, subtitle, activatable_widget: check});
            row.add_prefix(check);
            check.connect('toggled', () => {
                if (check.active && settings.get_string('background') !== value)
                    settings.set_string('background', value);
            });
            checks[value] = check;
            around.add(row);
            if (value === 'color')
                colorRow = row;
        }

        const colorButton = new Gtk.ColorDialogButton({
            dialog: new Gtk.ColorDialog({title: 'Background Color', with_alpha: false}),
            rgba: hexToRgba(settings.get_string('background-color')),
            valign: Gtk.Align.CENTER,
        });
        colorButton.connect('notify::rgba', () => {
            const hex = rgbaToHex(colorButton.rgba);
            if (hex !== settings.get_string('background-color'))
                settings.set_string('background-color', hex);
        });
        colorRow.add_suffix(colorButton);

        const updateBackground = () => {
            const value = settings.get_string('background');
            checks[value].active = true;
            colorButton.sensitive = value === 'color';
            const rgba = hexToRgba(settings.get_string('background-color'));
            if (!rgba.equal(colorButton.rgba))
                colorButton.rgba = rgba;
        };
        updateBackground();

        // ---------- About ----------
        const about = new Adw.PreferencesGroup({title: 'About'});
        page.add(about);
        about.add(new Adw.ActionRow({
            title: 'Version',
            subtitle: this.metadata['version-name'] ?? String(this.metadata.version ?? ''),
            css_classes: ['property'],
        }));
        about.add(new Adw.ActionRow({
            title: 'Author',
            subtitle: 'Luis Llana &lt;luis.llana.diaz@gmail.com&gt;',
            css_classes: ['property'],
        }));
        about.add(new Adw.ActionRow({
            title: 'License',
            subtitle: 'GNU General Public License v3.0 or later',
            css_classes: ['property'],
        }));

        // ---------- Keep in sync with the settings ----------
        const settingsId = settings.connect('changed', (_settings, key) => {
            if (['current-file', 'title', 'author', 'status'].includes(key))
                updateToday();
            else if (key === 'background' || key === 'background-color')
                updateBackground();
            else if (key === 'server-url' && urlRow.text.trim() !== settings.get_string('server-url'))
                urlRow.text = settings.get_string('server-url');
        });
        window.connect('close-request', () => {
            settings.disconnect(settingsId);
            session.abort();
            return false;
        });
    }
}
