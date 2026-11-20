# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
import io
import os
import sys
import unittest

from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from catholic_background_gtk import compose  # noqa: E402


def picture(width, height, color="#c08040"):
    data = io.BytesIO()
    Image.new("RGB", (width, height), color).save(data, "PNG")
    return data.getvalue()


class ComposeTest(unittest.TestCase):
    def test_size_of_the_screen(self):
        for mode in ("blur", "average", "color"):
            result = Image.open(io.BytesIO(compose.compose(picture(600, 900), 1920, 1080, mode, "#102030", 32)))
            self.assertEqual(result.size, (1920, 1080), mode)

    def test_color_around_a_portrait(self):
        result = Image.open(io.BytesIO(compose.compose(picture(600, 900), 1920, 1080, "color", "#ff0000", 0)))
        r, g, b = result.convert("RGB").getpixel((10, 540))
        self.assertTrue(r > 230 and g < 30 and b < 30)
        r, g, b = result.convert("RGB").getpixel((960, 540))
        self.assertTrue(abs(r - 0xc0) < 10 and abs(g - 0x80) < 10)


if __name__ == "__main__":
    unittest.main()
