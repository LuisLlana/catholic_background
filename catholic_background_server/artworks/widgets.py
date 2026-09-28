# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
from django import forms


class DropImageWidget(forms.ClearableFileInput):
    """Image field with an area to drag and drop the file (or click to choose it) and a preview."""

    template_name = "artworks/widgets/drop_image.html"

    def __init__(self, attrs=None):
        super().__init__({"accept": "image/jpeg,image/png", **(attrs or {})})
