# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Museum-style label drawn below the artwork: the reason why it is shown that day, its title
and its author and year. The applications fit the whole image (artwork + label) on the screen,
so the size of the text is computed for a 16:9 screen.
"""
import hashlib
import io
import logging
from pathlib import Path

from django.conf import settings
from PIL import Image, ImageDraw, ImageFont, ImageOps

logger = logging.getLogger(__name__)

# Change it when the look of the label changes, so that cached images are drawn again
VERSION = "1"

BAND = (22, 22, 24)
COLORS = {"reason": (240, 194, 75), "title": (255, 255, 255), "author": (205, 205, 205)}
# Height of each kind of text as a fraction of the height of a 16:9 screen
SIZES = {"reason": 0.020, "title": 0.027, "author": 0.020}
FONT_FILES = {
    "regular": ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "DejaVuSans.ttf"],
    "bold": ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "DejaVuSans-Bold.ttf"],
}


def _font(weight, size):
    custom = settings.CATHOLIC_BACKGROUND.get("CAPTION_FONT" if weight == "regular" else "CAPTION_FONT_BOLD")
    for file in ([custom] if custom else []) + FONT_FILES[weight]:
        try:
            return ImageFont.truetype(file, size)
        except OSError:
            continue
    logger.warning("No font with accents found for the captions: install fonts-dejavu-core")
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _wrap(draw, text, font, width, max_lines):
    """Lines no wider than width; the last one ends with … if the text does not fit."""
    lines, current = [], ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if not current or draw.textlength(candidate, font=font) <= width:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        while lines[-1] and draw.textlength(lines[-1] + "…", font=font) > width:
            lines[-1] = lines[-1][:-1]
        lines[-1] = lines[-1].rstrip() + "…"
    return lines


def add_label(image, reason, title, author_year):
    """Returns a new RGB image: the artwork with the label below it (or the artwork alone if there is no text)."""
    image = ImageOps.exif_transpose(image).convert("RGB")
    if not (reason or title or author_year):
        return image
    width, height = image.size
    # Height of a 16:9 screen on which the image would be fitted, in pixels of the image
    screen = max(height * 1.12, width * 9 / 16)
    padding = round(screen * 0.018)
    gap = round(screen * 0.006)
    max_width = width - 2 * padding
    fonts = {
        "reason": _font("regular", max(10, round(screen * SIZES["reason"]))),
        "title": _font("bold", max(12, round(screen * SIZES["title"]))),
        "author": _font("regular", max(10, round(screen * SIZES["author"]))),
    }
    measure = ImageDraw.Draw(image)
    lines = []
    title_lines = 2 if width >= height else 3
    for kind, text, max_lines in (("reason", reason, 1), ("title", title, title_lines), ("author", author_year, 1)):
        if text:
            lines += [(kind, line) for line in _wrap(measure, text, fonts[kind], max_width, max_lines)]
    heights = [fonts[kind].getbbox("ÁÉgjpq")[3] for kind, _ in lines]
    band = 2 * padding + sum(heights) + gap * (len(lines) - 1)

    labelled = Image.new("RGB", (width, height + band), BAND)
    labelled.paste(image, (0, 0))
    draw = ImageDraw.Draw(labelled)
    y = height + padding
    for (kind, line), line_height in zip(lines, heights):
        draw.text((padding, y), line, font=fonts[kind], fill=COLORS[kind])
        y += line_height + gap
    return labelled


def labelled_jpeg(artwork, texts, reason):
    """
    JPEG bytes of the artwork with its label, cached on disk: the same request always gets
    exactly the same bytes (the applications compare them to detect a new image).
    """
    author_year = ", ".join(t for t in (texts["author"], texts["year"]) if t)
    key = hashlib.sha256("\x1f".join([
        VERSION, artwork.image.name, str(artwork.image.size), reason, texts["title"], author_year,
    ]).encode()).hexdigest()
    cache = Path(settings.MEDIA_ROOT) / "caption-cache"
    path = cache / f"{key}.jpg"
    if path.exists():
        path.touch()          # recently used: kept by the nightly clean-up
        return path.read_bytes()
    with artwork.image.open("rb") as f:
        labelled = add_label(Image.open(io.BytesIO(f.read())), reason, texts["title"], author_year)
    buffer = io.BytesIO()
    labelled.save(buffer, "JPEG", quality=90)
    data = buffer.getvalue()
    cache.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)
    return data
