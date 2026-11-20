# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Settings and state, in ~/.config/catholic-background-gtk/settings.json."""

import json
import os

from gi.repository import GLib

from .server import DEFAULT_SERVER, system_language

APP_ID = "es.llana.CatholicBackground"
DEFAULTS = {
    # Settings
    "server": DEFAULT_SERVER,
    "language": "",             # "" = that of the system
    "label": True,              # reason, title and author below the artwork (drawn by the server)
    "background": "blur",       # around the image: "blur", "average" or "color"
    "color": "#000000",
    "wallpaper": False,         # keep the image of the day as the desktop background
    "lock_screen": False,       # also as the lock screen background
    "notify": True,             # notification when the image changes
    "interval": 30,             # minutes between checks
    # State
    "image_hash": "",           # SHA-1 of the image last set
    "composed": "",             # settings and screen of the composition last set
    "show_date": "",            # day chosen with "Use as wallpaper" (ISO), until the next check
    "last_check": "",
    "last_result": "",
    "reason": "", "title": "", "author": "",
    "screen": [1920, 1080, 0],  # width, height and top bar of the primary monitor, in pixels
}


def config_dir():
    return os.path.join(GLib.get_user_config_dir(), "catholic-background-gtk")


def data_dir():
    return os.path.join(GLib.get_user_data_dir(), "backgrounds", "catholic-background")


class Settings(dict):
    """The settings as a dict; save() writes them (atomically)."""

    def __init__(self):
        super().__init__(DEFAULTS)
        self.path = os.path.join(config_dir(), "settings.json")
        try:
            with open(self.path, encoding="utf-8") as f:
                stored = json.load(f)
            self.update({k: v for k, v in stored.items() if k in DEFAULTS})
        except (OSError, ValueError):
            pass

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        temporary = self.path + ".tmp"
        with open(temporary, "w", encoding="utf-8") as f:
            json.dump(self, f, indent=2, ensure_ascii=False)
        os.replace(temporary, self.path)

    def language_code(self):
        return self["language"] or system_language()
