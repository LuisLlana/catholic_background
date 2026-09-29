// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Access to the Catholic background of the day server. Used both by the
// extension and by the preferences window (only GLib, Gio, Soup and GdkPixbuf).
//
// Protocol:  GET <url>?ts=<Unix timestamp of the local midnight of the day>&lang=<language>[&caption=0]
//            -> {"image": "<base64>", "title", "author", "date", "description", "reason",
//                "license", "source", "extra", "language", "edit_url", ...}
//            GET <url>/languages -> {"default": "es", "languages": [{"code", "name"}, ...]}
//
// The extension and the preferences build the address of the wallpaper in the same way
// (wallpaperUrl), so that both would get exactly the same image.

import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import GdkPixbuf from 'gi://GdkPixbuf';
import Soup from 'gi://Soup?version=3.0';

Gio._promisify(Soup.Session.prototype, 'send_and_read_async');

/** Today's local midnight as a GLib.DateTime. */
export function todayMidnight() {
    const now = GLib.DateTime.new_now_local();
    return GLib.DateTime.new_local(now.get_year(), now.get_month(), now.get_day_of_month(), 0, 0, 0);
}

/** Local midnight of a day (month 1–12) as a GLib.DateTime. */
export function midnight(year, month, day) {
    return GLib.DateTime.new_local(year, month, day, 0, 0, 0);
}

/** "YYYY-MM-DD" of a GLib.DateTime. */
export function isoDate(date) {
    return date.format('%Y-%m-%d');
}

/** Language of the system as a code such as "es-es" ('' if it is C or POSIX). */
export function systemLanguage() {
    const name = GLib.get_language_names()[0] ?? '';
    const code = name.split('.')[0].split('@')[0].replace('_', '-').toLowerCase();
    return code === 'c' || code === 'posix' ? '' : code;
}

/** Language of the texts: the one chosen in the settings, or else that of the system. */
export function languageCode(settings) {
    return settings.get_string('language') || systemLanguage();
}

/** Day of the wallpaper: the one chosen with "Use as wallpaper", or today. */
export function wallpaperDay(settings) {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(settings.get_string('show-date'));
    return match ? midnight(Number(match[1]), Number(match[2]), Number(match[3])) : todayMidnight();
}

/** Address of the image of the wallpaper, according to the settings. */
export function wallpaperUrl(settings) {
    return requestUrl(settings.get_string('server-url'), wallpaperDay(settings).to_unix(),
        languageCode(settings), settings.get_boolean('show-label'));
}

/** Throws an Error with a readable message if the URL is not valid. */
export function validateUrl(baseUrl) {
    requestUrl(baseUrl, 0, '', true);
}

/** base?ts=<ts>&lang=<language>[&caption=0], keeping any other query parameters. */
export function requestUrl(baseUrl, ts, language = '', label = true) {
    const uri = GLib.Uri.parse(baseUrl.trim(), GLib.UriFlags.NONE);
    const scheme = uri.get_scheme();
    if (scheme !== 'http' && scheme !== 'https')
        throw new Error('The URL must start with http:// or https://');

    const params = [];
    const query = uri.get_query();
    if (query) {
        for (const part of query.split('&')) {
            if (part && !['ts', 'lang', 'caption'].includes(part.split('=')[0]))
                params.push(part);
        }
    }
    params.push(`ts=${ts}`);
    if (language)
        params.push(`lang=${GLib.Uri.escape_string(language, null, false)}`);
    if (!label)
        params.push('caption=0');

    return GLib.Uri.build(GLib.UriFlags.ENCODED, scheme, uri.get_userinfo(), uri.get_host(),
        uri.get_port(), uri.get_path(), params.join('&'), uri.get_fragment()).to_string();
}

/** "Title (date)", "Title" or "date". */
export function formatTitle(title, date) {
    title = (title ?? '').trim();
    date = (date ?? '').toString().trim();
    if (title && date)
        return `${title} (${date})`;
    return title || date;
}

/** Decodes image bytes (GLib.Bytes) into a GdkPixbuf, honoring the EXIF orientation. */
export function pixbufFromBytes(bytes) {
    const loader = new GdkPixbuf.PixbufLoader();
    try {
        loader.write_bytes(bytes);
        loader.close();
    } catch (e) {
        throw new Error('The "image" field does not contain a valid image');
    }
    const pixbuf = loader.get_pixbuf();
    if (!pixbuf)
        throw new Error('The "image" field does not contain a valid image');
    return pixbuf.apply_embedded_orientation() ?? pixbuf;
}

async function getJson(session, url, cancellable) {
    const message = Soup.Message.new('GET', url);
    if (!message)
        throw new Error('The URL is not valid');

    let body;
    try {
        body = await session.send_and_read_async(message, GLib.PRIORITY_DEFAULT, cancellable);
    } catch (e) {
        if (e.matches?.(Gio.IOErrorEnum, Gio.IOErrorEnum.CANCELLED))
            throw e;
        throw new Error(`Could not connect to the server: ${e.message}`);
    }
    if (message.get_status() === Soup.Status.NOT_FOUND)
        throw new Error('There is no image for this day');
    if (message.get_status() !== Soup.Status.OK)
        throw new Error(`The server answered with HTTP ${message.get_status()} ${message.get_reason_phrase() ?? ''}`.trim());

    try {
        return JSON.parse(new TextDecoder().decode(body.get_data()));
    } catch (e) {
        throw new Error('The server did not answer with JSON');
    }
}

/** Languages of the content offered by the server (Spanish and English if it cannot be asked). */
export async function fetchLanguages(session, baseUrl, cancellable = null) {
    const fallback = [{code: 'es', name: 'Español'}, {code: 'en', name: 'English'}];
    try {
        const uri = GLib.Uri.parse(baseUrl.trim(), GLib.UriFlags.NONE);
        const url = GLib.Uri.build(GLib.UriFlags.ENCODED, uri.get_scheme(), uri.get_userinfo(), uri.get_host(),
            uri.get_port(), `${uri.get_path().replace(/\/+$/, '')}/languages`, null, null).to_string();
        const json = await getJson(session, url, cancellable);
        const found = (json.languages ?? []).filter(l => l && typeof l.code === 'string' && l.code);
        return found.length ? found.map(l => ({code: l.code, name: String(l.name ?? l.code)})) : fallback;
    } catch (e) {
        if (e.matches?.(Gio.IOErrorEnum, Gio.IOErrorEnum.CANCELLED))
            throw e;
        return fallback;
    }
}

/**
 * Downloads an image of the server (url: see requestUrl and wallpaperUrl).
 * Returns {bytes, pixbuf, title, year, titleWithYear, author, description, reason, license,
 * source, editUrl, language, extra: [[name, value], ...]}; bytes is the image (GLib.Bytes).
 * Throws an Error with a readable message on failure.
 */
export async function fetchWallpaper(session, url, cancellable = null) {
    const json = await getJson(session, url, cancellable);
    if (typeof json !== 'object' || json === null || typeof json.image !== 'string')
        throw new Error('The answer of the server has no "image" field');

    let base64 = json.image;
    if (base64.startsWith('data:'))
        base64 = base64.slice(base64.indexOf(',') + 1);
    let data;
    try {
        data = GLib.base64_decode(base64);
    } catch (e) {
        throw new Error('The "image" field is not valid base64');
    }
    const bytes = new GLib.Bytes(data);

    const text = name => (json[name] ?? '').toString().trim();
    const extra = typeof json.extra === 'object' && json.extra !== null
        ? Object.entries(json.extra).map(([k, v]) => [k, String(v ?? '').trim()]).filter(([, v]) => v) : [];
    return {
        bytes,
        pixbuf: pixbufFromBytes(bytes),
        title: text('title'),
        year: text('date'),
        titleWithYear: formatTitle(json.title, json.date),
        author: text('author'),
        description: text('description'),
        reason: text('reason'),
        license: text('license'),
        source: text('source'),
        editUrl: text('edit_url'),
        language: text('language'),
        extra,
    };
}
