// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Composes the wallpaper: the whole image, as big as possible without
// cropping it, inside the free area of the screen, on top of a background
// that covers the whole screen (blurred image, average color or a color).

import GLib from 'gi://GLib';
import GdkPixbuf from 'gi://GdkPixbuf';

const INTERP = GdkPixbuf.InterpType.BILINEAR;

/** Opaque RGB copy of a small pixbuf with its colors multiplied by factor. */
function darken(pixbuf, factor) {
    const rgba = pixbuf.add_alpha(false, 0, 0, 0);  // known layout: RGBA
    const src = rgba.read_pixel_bytes().toArray();
    const width = rgba.get_width(), height = rgba.get_height(), stride = rgba.get_rowstride();
    const out = new Uint8Array(width * height * 3);
    for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
            const i = y * stride + x * 4, o = (y * width + x) * 3;
            out[o] = Math.round(src[i] * factor);
            out[o + 1] = Math.round(src[i + 1] * factor);
            out[o + 2] = Math.round(src[i + 2] * factor);
        }
    }
    return GdkPixbuf.Pixbuf.new_from_bytes(new GLib.Bytes(out), GdkPixbuf.Colorspace.RGB, false, 8,
        width, height, width * 3);
}

/** Average color of the image as [r, g, b]. */
export function averageColor(pixbuf) {
    const small = pixbuf.scale_simple(64, 64, INTERP).add_alpha(false, 0, 0, 0);
    const data = small.read_pixel_bytes().toArray();
    const stride = small.get_rowstride();
    let r = 0, g = 0, b = 0, n = 0;
    for (let y = 0; y < 64; y++) {
        for (let x = 0; x < 64; x++) {
            const i = y * stride + x * 4;
            r += data[i];
            g += data[i + 1];
            b += data[i + 2];
            n++;
        }
    }
    return [Math.round(r / n), Math.round(g / n), Math.round(b / n)];
}

/** "#rrggbb" -> [r, g, b], black if not valid. */
export function parseColor(hex) {
    const m = /^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec((hex ?? '').trim());
    return m ? [parseInt(m[1], 16), parseInt(m[2], 16), parseInt(m[3], 16)] : [0, 0, 0];
}

/** [r, g, b] -> "#rrggbb" */
export function colorToHex([r, g, b]) {
    return `#${[r, g, b].map(v => v.toString(16).padStart(2, '0')).join('')}`;
}

function solid(width, height, [r, g, b]) {
    const canvas = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, false, 8, width, height);
    canvas.fill(((r << 24) | (g << 16) | (b << 8) | 0xff) >>> 0);
    return canvas;
}

/** The image enlarged to cover width x height, blurred and slightly darkened. */
function blurred(pixbuf, width, height) {
    // Part of the image with the proportions of the screen (like "zoom")
    const iw = pixbuf.get_width(), ih = pixbuf.get_height();
    let cw = iw, ch = Math.round(iw * height / width);
    if (ch > ih) {
        ch = ih;
        cw = Math.round(ih * width / height);
    }
    const crop = pixbuf.new_subpixbuf(Math.floor((iw - cw) / 2), Math.floor((ih - ch) / 2), cw, ch);

    // Blur: shrink to a few pixels and enlarge again in smooth steps
    const tinyWidth = 16;
    let result = darken(crop.scale_simple(tinyWidth, Math.max(1, Math.round(tinyWidth * height / width)), INTERP), 0.73);
    while (result.get_width() * 4 < width)
        result = result.scale_simple(result.get_width() * 2, result.get_height() * 2, INTERP);
    return result.scale_simple(width, height, INTERP);
}

/**
 * @param {GdkPixbuf.Pixbuf} pixbuf  the original image
 * @param {object} screen  {width, height} of the screen in pixels
 * @param {object} free    {x, y, width, height}: area of the screen not covered by panels
 * @param {string} mode    'blur', 'average' or 'color'
 * @param {string} color   '#rrggbb' for mode 'color'
 * @returns {{pixbuf: GdkPixbuf.Pixbuf, fillColor: number[]}}
 */
export function compose(pixbuf, screen, free, mode, color) {
    const {width, height} = screen;
    let canvas, fillColor;
    if (mode === 'color') {
        fillColor = parseColor(color);
        canvas = solid(width, height, fillColor);
    } else if (mode === 'average') {
        fillColor = averageColor(pixbuf);
        canvas = solid(width, height, fillColor);
    } else {
        fillColor = averageColor(pixbuf);
        canvas = blurred(pixbuf, width, height);
    }

    // Ignore absurd free areas
    let area = free;
    if (!area || area.width < width / 2 || area.height < height / 2)
        area = {x: 0, y: 0, width, height};

    // Largest size that keeps the proportions and fits entirely in the area
    const scale = Math.min(area.width / pixbuf.get_width(), area.height / pixbuf.get_height());
    const fw = Math.max(1, Math.round(pixbuf.get_width() * scale));
    const fh = Math.max(1, Math.round(pixbuf.get_height() * scale));
    const x = area.x + Math.floor((area.width - fw) / 2);
    const y = area.y + Math.floor((area.height - fh) / 2);

    const fitted = pixbuf.scale_simple(fw, fh, INTERP);
    fitted.composite(canvas, x, y, fw, fh, x, y, 1, 1, GdkPixbuf.InterpType.NEAREST, 255);

    return {pixbuf: canvas, fillColor};
}
