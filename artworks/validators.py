# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
from django.conf import settings
from django.core.exceptions import ValidationError
from PIL import Image


def validate_image(file):
    opts = settings.CATHOLIC_BACKGROUND
    if file.size > opts["MAX_IMAGE_MB"] * 1024 * 1024:
        raise ValidationError(f"La imagen ocupa más de {opts['MAX_IMAGE_MB']} MB.")
    try:
        file.seek(0)
        with Image.open(file) as image:
            fmt, (width, height) = image.format, image.size
    except Exception:
        raise ValidationError("El fichero no es una imagen válida.")
    finally:
        file.seek(0)
    if fmt not in ("JPEG", "PNG"):
        raise ValidationError(f"Formato {fmt} no admitido: usa JPEG o PNG.")
    if max(width, height) < opts["MIN_IMAGE_SIDE"]:
        raise ValidationError(
            f"La imagen es demasiado pequeña ({width}×{height}): el lado mayor debe tener al menos "
            f"{opts['MIN_IMAGE_SIDE']} píxeles.")
