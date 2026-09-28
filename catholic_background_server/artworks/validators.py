# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from PIL import Image


def validate_image(file):
    opts = settings.CATHOLIC_BACKGROUND
    if file.size > opts["MAX_IMAGE_MB"] * 1024 * 1024:
        raise ValidationError(_("The image is larger than %(size)s MB.") % {"size": opts["MAX_IMAGE_MB"]})
    try:
        file.seek(0)
        with Image.open(file) as image:
            fmt, (width, height) = image.format, image.size
    except Exception:
        raise ValidationError(_("The file is not a valid image."))
    finally:
        file.seek(0)
    if fmt not in ("JPEG", "PNG"):
        raise ValidationError(_("%(format)s is not supported: use JPEG or PNG.") % {"format": fmt})
    if max(width, height) < opts["MIN_IMAGE_SIDE"]:
        raise ValidationError(
            _("The image is too small (%(width)s×%(height)s): its longest side must have at least %(min)s pixels.")
            % {"width": width, "height": height, "min": opts["MIN_IMAGE_SIDE"]})
