// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Access to the Catholic background of the day server. Used both by the
// extension and by the preferences window (only GLib, Gio, Soup and GdkPixbuf).
//
// Protocol:  GET <url>?ts=<Unix timestamp of today's local midnight>
//            -> {"image": "<base64>", "title": ..., "author": ..., "date": ...}

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

/** Base URL with ts=<timestamp>, keeping any other query parameters. */
export function urlForTimestamp(baseUrl, ts) {
    const uri = GLib.Uri.parse(baseUrl.trim(), GLib.UriFlags.NONE);
    const scheme = uri.get_scheme();
    if (scheme !== 'http' && scheme !== 'https')
        throw new Error('The URL must start with http:// or https://');

    const params = [];
    const query = uri.get_query();
    if (query) {
        for (const part of query.split('&')) {
            if (part && part.split('=')[0] !== 'ts')
                params.push(part);
        }
    }
    params.push(`ts=${ts}`);

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

/**
 * Downloads today's wallpaper.
 * Returns {bytes, pixbuf, title, author} where bytes is the original image (GLib.Bytes).
 * Throws an Error with a readable message on failure.
 */
export async function fetchWallpaper(session, baseUrl, cancellable = null) {
    const url = urlForTimestamp(baseUrl, todayMidnight().to_unix());
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
    if (message.get_status() !== Soup.Status.OK)
        throw new Error(`The server answered with HTTP ${message.get_status()} ${message.get_reason_phrase() ?? ''}`.trim());

    let json;
    try {
        json = JSON.parse(new TextDecoder().decode(body.get_data()));
    } catch (e) {
        throw new Error('The server did not answer with JSON');
    }
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

    return {
        bytes,
        pixbuf: pixbufFromBytes(bytes),
        title: formatTitle(json.title, json.date),
        author: (json.author ?? '').toString().trim(),
    };
}
