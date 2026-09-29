// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later

import Adw from 'gi://Adw';
import Gdk from 'gi://Gdk';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Gtk from 'gi://Gtk';
import Pango from 'gi://Pango';
import Soup from 'gi://Soup?version=3.0';

import {ExtensionPreferences} from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';

import {
    fetchLanguages, fetchWallpaper, isoDate, languageCode, midnight, requestUrl, systemLanguage,
    todayMidnight, validateUrl, wallpaperDay,
} from './lib/server.js';

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

/** Long date in the language of the system: "martes, 29 de septiembre de 2026". */
function longDate(date) {
    try {
        const locale = systemLanguage() || undefined;
        return new Date(date.get_year(), date.get_month() - 1, date.get_day_of_month())
            .toLocaleDateString(locale, {weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'});
    } catch (e) {
        return date.format('%A %e %B %Y');
    }
}

function noHyphens() {
    const attributes = new Pango.AttrList();
    attributes.insert(Pango.attr_insert_hyphens_new(false));
    return attributes;
}

function sameDay(a, b) {
    return isoDate(a) === isoDate(b);
}

/** Adwaita pages are narrow (a clamp of 600 px): the page of the image uses the whole window. */
function widenPage(widget) {
    for (let child = widget.get_first_child(); child; child = child.get_next_sibling()) {
        if (child instanceof Adw.Clamp) {
            child.maximum_size = 4000;
            child.tightening_threshold = 4000;
        }
        widenPage(child);
    }
}

export default class CatholicBackgroundPreferences extends ExtensionPreferences {
    fillPreferencesWindow(window) {
        const settings = this.getSettings();
        const session = new Soup.Session({timeout: 60});
        window._settings = settings;
        window.set_default_size(1100, 820);
        window.search_enabled = false;
        const toast = title => window.add_toast(new Adw.Toast({title, timeout: 5}));

        window.add(this._dayPage(window, settings, session, toast));
        window.add(this._settingsPage(window, settings, session, toast));
    }

    // ------------------------------------------------------------------ image of the day

    _dayPage(window, settings, session, toast) {
        const page = new Adw.PreferencesPage({
            title: 'Image of the Day',
            icon_name: 'image-x-generic-symbolic',
            name: 'day',
        });
        const group = new Adw.PreferencesGroup();
        page.add(group);
        page.connect('realize', () => widenPage(page));

        let viewDay = todayMidnight();
        let loaded = null;              // data of the day shown
        let loading = null;             // Gio.Cancellable of the current download

        // ---- choice of the day ... actions
        const bar = new Gtk.Box({spacing: 6, margin_bottom: 6});
        const previous = new Gtk.Button({icon_name: 'go-previous-symbolic', tooltip_text: 'Previous day'});
        const next = new Gtk.Button({icon_name: 'go-next-symbolic', tooltip_text: 'Next day'});
        const calendar = new Gtk.Calendar();
        const todayInPopover = new Gtk.Button({label: 'Today', halign: Gtk.Align.CENTER});
        const popoverBox = new Gtk.Box({orientation: Gtk.Orientation.VERTICAL, spacing: 6});
        popoverBox.append(calendar);
        popoverBox.append(todayInPopover);
        const popover = new Gtk.Popover({child: popoverBox});
        const dateLabel = new Gtk.Label();
        const dateButtonBox = new Gtk.Box({spacing: 6});
        dateButtonBox.append(new Gtk.Image({icon_name: 'x-office-calendar-symbolic'}));
        dateButtonBox.append(dateLabel);
        const dateButton = new Gtk.MenuButton({child: dateButtonBox, popover, tooltip_text: 'Choose a day'});
        const today = new Gtk.Button({label: 'Today'});
        const use = new Gtk.Button({label: 'Use as Wallpaper', css_classes: ['suggested-action']});
        const edit = new Gtk.Button({label: 'Edit this Image', tooltip_text: 'Opens the page of the artwork in the content manager'});
        const spacer = new Gtk.Box({hexpand: true});
        for (const widget of [previous, dateButton, next, today, spacer, use, edit])
            bar.append(widget);
        group.add(bar);

        const note = new Gtk.Label({xalign: 0, wrap: true, css_classes: ['dim-label'], margin_bottom: 6});
        group.add(note);

        // ---- the image (two thirds) and its data
        const content = new Gtk.Box({spacing: 18});
        group.add(content);

        const picture = new Gtk.Picture({content_fit: Gtk.ContentFit.CONTAIN, can_shrink: true});
        const spinner = new Adw.Spinner({width_request: 48, height_request: 48, halign: Gtk.Align.CENTER, valign: Gtk.Align.CENTER});
        const message = new Adw.StatusPage({icon_name: 'image-missing-symbolic', css_classes: ['compact']});
        const stack = new Gtk.Stack({
            css_classes: ['card'], overflow: Gtk.Overflow.HIDDEN, hexpand: true,
            width_request: 420, height_request: 560,
        });
        stack.add_named(picture, 'picture');
        stack.add_named(spinner, 'loading');
        stack.add_named(message, 'message');
        content.append(stack);

        // About a third of the width: the texts wrap instead of widening the column
        const info = new Gtk.Box({orientation: Gtk.Orientation.VERTICAL, spacing: 4, width_request: 300, hexpand: false, valign: Gtk.Align.START});
        content.append(info);
        const label = (css, extra = {}) => {
            const l = new Gtk.Label({xalign: 0, wrap: true, wrap_mode: Pango.WrapMode.WORD_CHAR, max_width_chars: 36, selectable: true, css_classes: css, ...extra});
            info.append(l);
            return l;
        };
        const reason = label(['accent', 'heading']);
        const title = label(['title-2']);
        const authorYear = label(['title-4']);
        const description = label([], {margin_top: 10});
        const details = new Gtk.Grid({column_spacing: 12, row_spacing: 4, margin_top: 12});
        info.append(details);

        // ---- last check and refresh
        const bottom = new Gtk.Box({spacing: 12, margin_top: 12});
        const status = new Gtk.Label({xalign: 0, hexpand: true, wrap: true, css_classes: ['dim-label', 'caption']});
        const refresh = new Gtk.Button({label: 'Refresh Wallpaper', tooltip_text: 'Download the image of the wallpaper again'});
        bottom.append(status);
        bottom.append(refresh);
        group.add(bottom);

        const showDetails = data => {
            for (let child = details.get_first_child(); child; child = details.get_first_child())
                details.remove(child);
            const rows = [...data.extra];
            if (data.license)
                rows.push(['License', data.license]);
            if (data.source)
                rows.push(['Source', data.source]);
            rows.forEach(([name, value], i) => {
                details.attach(new Gtk.Label({label: name, xalign: 0, yalign: 0, css_classes: ['heading']}), 0, i, 1, 1);
                const valueLabel = name === 'Source' && value === data.source
                    ? new Gtk.Label({
                        label: `<a href="${GLib.markup_escape_text(value, -1)}">${GLib.markup_escape_text(value, -1)}</a>`,
                        use_markup: true, xalign: 0, wrap: true, wrap_mode: Pango.WrapMode.CHAR, max_width_chars: 28, hexpand: true,
                        attributes: noHyphens(),   // an address must not get hyphens where it is split
                    })
                    : new Gtk.Label({label: value, xalign: 0, wrap: true, max_width_chars: 28, selectable: true, hexpand: true});
                details.attach(valueLabel, 1, i, 1, 1);
            });
        };

        const updateState = () => {
            const wallpaper = wallpaperDay(settings);
            const isWallpaper = sameDay(viewDay, wallpaper);
            dateLabel.label = longDate(viewDay);
            today.sensitive = !sameDay(viewDay, todayMidnight());
            use.label = isWallpaper ? 'This Is Your Wallpaper' : 'Use as Wallpaper';
            use.sensitive = !isWallpaper && loaded !== null;
            edit.visible = loaded !== null && loaded.editUrl !== '';
            note.visible = !sameDay(wallpaper, todayMidnight());
            note.label = `The wallpaper shows the image of ${longDate(wallpaper)} until the next automatic check, which returns to today.`;
            status.label = settings.get_string('status');
        };

        const load = async day => {
            loading?.cancel();
            const cancellable = loading = new Gio.Cancellable();
            viewDay = day;
            loaded = null;
            stack.visible_child_name = 'loading';
            info.visible = false;
            updateState();
            let data;
            try {
                // The artwork alone: its data are shown next to it
                const url = requestUrl(settings.get_string('server-url'), day.to_unix(), languageCode(settings), false);
                data = await fetchWallpaper(session, url, cancellable);
            } catch (e) {
                if (e.matches?.(Gio.IOErrorEnum, Gio.IOErrorEnum.CANCELLED) || cancellable !== loading)
                    return;
                message.title = e.message;
                stack.visible_child_name = 'message';
                updateState();
                return;
            }
            if (cancellable !== loading)
                return;
            loaded = data;
            picture.set_paintable(Gdk.Texture.new_for_pixbuf(data.pixbuf));
            stack.visible_child_name = 'picture';
            reason.label = data.reason;
            reason.visible = data.reason !== '';
            title.label = data.title || 'Untitled';
            authorYear.label = [data.author, data.year].filter(Boolean).join(', ');
            authorYear.visible = authorYear.label !== '';
            description.label = data.description;
            description.visible = data.description !== '';
            showDetails(data);
            info.visible = true;
            updateState();
        };

        const shift = days => load(viewDay.add_days(days));
        previous.connect('clicked', () => shift(-1));
        next.connect('clicked', () => shift(1));
        today.connect('clicked', () => load(todayMidnight()));
        popover.connect('show', () => {
            calendar.year = viewDay.get_year();
            calendar.month = viewDay.get_month() - 1;
            calendar.day = viewDay.get_day_of_month();
        });
        calendar.connect('day-selected', () => {
            popover.popdown();
            load(midnight(calendar.year, calendar.month + 1, calendar.day));
        });
        todayInPopover.connect('clicked', () => {
            popover.popdown();
            load(todayMidnight());
        });
        use.connect('clicked', () => {
            // The extension downloads the image of that day; the next automatic check returns to today
            settings.set_string('show-date', sameDay(viewDay, todayMidnight()) ? '' : isoDate(viewDay));
            settings.set_int64('refresh-request', GLib.get_real_time());
            toast('Setting the wallpaper\u2026');
            updateState();
        });
        edit.connect('clicked', () => {
            if (loaded?.editUrl)
                new Gtk.UriLauncher({uri: loaded.editUrl}).launch(window, null, null);
        });
        refresh.connect('clicked', () => {
            settings.set_int64('refresh-request', GLib.get_real_time());
            toast('Downloading the image again\u2026');
        });

        const ids = [
            settings.connect('changed::show-date', updateState),
            settings.connect('changed::status', updateState),
            // The texts of the day in the new language, or from the new server
            settings.connect('changed::language', () => load(viewDay)),
            settings.connect('changed::server-url', () => load(viewDay)),
        ];
        window.connect('close-request', () => {
            loading?.cancel();
            ids.forEach(id => settings.disconnect(id));
            return false;
        });

        load(viewDay);
        return page;
    }

    // ------------------------------------------------------------------ settings

    _settingsPage(window, settings, session, toast) {
        const page = new Adw.PreferencesPage({
            title: 'Settings',
            icon_name: 'preferences-system-symbolic',
            name: 'settings',
        });

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
                validateUrl(url);
            } catch (e) {
                toast(e.message);
                return;
            }
            settings.set_string('server-url', url);
            toast('Server saved. Downloading the image\u2026');
        });

        const testButton = new Gtk.Button({
            label: 'Test',
            tooltip_text: 'Check the server without changing the wallpaper',
            valign: Gtk.Align.CENTER,
        });
        testButton.connect('clicked', async () => {
            testButton.sensitive = false;
            try {
                const url = requestUrl(urlRow.text, todayMidnight().to_unix(), languageCode(settings), false);
                const result = await fetchWallpaper(session, url, null);
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
        resetButton.connect('clicked', () => {
            settings.reset('server-url');
            urlRow.text = settings.get_string('server-url');
        });
        urlRow.add_suffix(resetButton);
        server.add(urlRow);

        const intervalRow = new Adw.SpinRow({
            title: 'Check every',
            subtitle: 'Minutes. The wallpaper changes only when the server has a different image.',
            adjustment: new Gtk.Adjustment({lower: 5, upper: 1440, step_increment: 5, page_increment: 60}),
        });
        settings.bind('check-interval', intervalRow, 'value', Gio.SettingsBindFlags.DEFAULT);
        server.add(intervalRow);

        // ---------- Texts ----------
        const texts = new Adw.PreferencesGroup({title: 'Texts'});
        page.add(texts);

        const systemName = (() => {
            try {
                const code = systemLanguage();
                const name = code ? new Intl.DisplayNames([code], {type: 'language'}).of(code) : '';
                return name ? name.charAt(0).toUpperCase() + name.slice(1) : code;
            } catch (e) {
                return systemLanguage();
            }
        })();
        const codes = [''];
        const names = new Gtk.StringList({strings: [`System language${systemName ? ` (${systemName})` : ''}`]});
        const languageRow = new Adw.ComboRow({
            title: 'Language',
            subtitle: 'Of the texts of the label and of the image of the day',
            model: names,
        });
        texts.add(languageRow);
        let fillingLanguages = true;
        languageRow.connect('notify::selected', () => {
            if (!fillingLanguages && codes[languageRow.selected] !== undefined)
                settings.set_string('language', codes[languageRow.selected]);
        });
        fetchLanguages(session, settings.get_string('server-url')).then(languages => {
            for (const language of languages) {
                codes.push(language.code);
                names.append(language.name);
            }
            languageRow.selected = Math.max(0, codes.indexOf(settings.get_string('language')));
            fillingLanguages = false;
        }).catch(() => {
            fillingLanguages = false;
        });

        const labelRow = new Adw.SwitchRow({
            title: 'Label below the artwork',
            subtitle: 'Why it is shown that day, its title, author and year',
        });
        settings.bind('show-label', labelRow, 'active', Gio.SettingsBindFlags.DEFAULT);
        texts.add(labelRow);

        // ---------- Around the image ----------
        const around = new Adw.PreferencesGroup({
            title: 'Around the Image',
            description: 'The image is always shown complete and as big as possible. Choose how to fill the rest of the screen.',
        });
        page.add(around);

        const checks = {};
        let firstCheck = null;
        let colorRow = null;
        for (const [value, title, subtitle] of [
            ['blur', 'Blurred image', 'The image enlarged and blurred'],
            ['average', 'Average color', 'The average color of the image'],
            ['color', 'Color', 'A color of your choice'],
        ]) {
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
        const ids = [
            settings.connect('changed::background', updateBackground),
            settings.connect('changed::background-color', updateBackground),
            settings.connect('changed::server-url', () => {
                urlRow.text = settings.get_string('server-url');
            }),
        ];
        window.connect('close-request', () => {
            ids.forEach(id => settings.disconnect(id));
            return false;
        });

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

        return page;
    }
}
