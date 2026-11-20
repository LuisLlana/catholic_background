# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
The wallpaper: the whole image, as big as possible without cropping it, inside the area of the
screen not covered by the top bar, over a background that covers the whole screen (the image
enlarged and blurred, its average color, or a color). The same as the other applications.
"""

import io
import re

from PIL import Image, ImageFilter, ImageOps, ImageStat


def parse_color(text):
    match = re.fullmatch(r"#?([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})", (text or "").strip())
    return tuple(int(part, 16) for part in match.groups()) if match else (0, 0, 0)


def open_image(data):
    return ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")


def average_color(image):
    return tuple(int(v) for v in ImageStat.Stat(image.resize((64, 64))).mean)


def compose(data, width, height, mode="blur", color="#000000", top=0):
    """
    data: the original image (bytes). width x height: the screen in pixels; top: pixels taken by
    the top bar. mode: "blur", "average" or "color". Returns JPEG bytes.
    """
    image = open_image(data)
    if mode == "color":
        canvas = Image.new("RGB", (width, height), parse_color(color))
    elif mode == "average":
        canvas = Image.new("RGB", (width, height), average_color(image))
    else:
        cover = ImageOps.fit(image, (max(1, width // 8), max(1, height // 8)), Image.BILINEAR)
        cover = cover.filter(ImageFilter.GaussianBlur(6)).point(lambda v: int(v * 0.73))
        canvas = cover.resize((width, height), Image.BILINEAR)
    top = top if 0 <= top < height // 4 else 0
    area_height = height - top
    scale = min(width / image.width, area_height / image.height)
    fitted = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))), Image.LANCZOS)
    canvas.paste(fitted, ((width - fitted.width) // 2, top + (area_height - fitted.height) // 2))
    output = io.BytesIO()
    canvas.save(output, "JPEG", quality=92)
    return output.getvalue()
