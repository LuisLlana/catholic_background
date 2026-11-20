# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Desktop and lock screen backgrounds of GNOME (GSettings), and the periodic check that keeps them
up to date (catholic-background-gtk --update, run by a systemd user timer).
"""

import datetime
import glob
import hashlib
import json
import os
import subprocess

from gi.repository import Gio, GLib

from . import compose as composer
from .config import APP_ID, Settings, data_dir
from .server import ServerError, fetch, request_url, title_with_year

DESKTOP = "org.gnome.desktop.background"
LOCK = "org.gnome.desktop.screensaver"


def _gsettings(schema):
    """Gio.Settings of a schema, or None if this desktop does not have it."""
    source = Gio.SettingsSchemaSource.get_default()
    found = source.lookup(schema, True) if source else None
    return (Gio.Settings.new(schema), found) if found else (None, None)


def _set_picture(schema, uri):
    settings, found = _gsettings(schema)
    if settings is None:
        return False
    settings.set_string("picture-uri", uri)
    if found.has_key("picture-uri-dark"):
        settings.set_string("picture-uri-dark", uri)
    if found.has_key("picture-options"):
        settings.set_string("picture-options", "zoom")   # the composition already has the screen's proportions
    Gio.Settings.sync()
    return True


def _get_picture(schema):
    settings, _ = _gsettings(schema)
    return settings.get_string("picture-uri") if settings else ""


def previous_file():
    return os.path.join(data_dir(), "previous.json")


def remember_previous(schema):
    """The background before ours, to give it back when the option is turned off."""
    stored = _read_json(previous_file())
    if schema not in stored:
        current = _get_picture(schema)
        if current and "catholic-background" not in current:
            stored[schema] = current
            _write_json(previous_file(), stored)


def restore_previous(schema):
    stored = _read_json(previous_file())
    uri = stored.pop(schema, "")
    if uri:
        _set_picture(schema, uri)
        _write_json(previous_file(), stored)


def _read_json(file):
    try:
        with open(file, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _write_json(file, data):
    os.makedirs(os.path.dirname(file), exist_ok=True)
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f)


def detect_screen(settings):
    """Size of the biggest monitor and of the top bar, in pixels, if there is a display."""
    try:
        import gi
        gi.require_version("Gtk", "4.0")
        gi.require_version("Gdk", "4.0")
        from gi.repository import Gdk, Gtk
        if not Gtk.init_check():
            return
        display = Gdk.Display.get_default()
        monitors = display.get_monitors() if display else None
        best = None
        for index in range(monitors.get_n_items() if monitors else 0):
            monitor = monitors.get_item(index)
            geometry, scale = monitor.get_geometry(), monitor.get_scale_factor()
            size = (geometry.width * scale, geometry.height * scale, 32 * scale)
            if best is None or size[0] * size[1] > best[0] * best[1]:
                best = size
        if best:
            settings["screen"] = list(best)
    except (ImportError, ValueError, AttributeError):
        pass


def start_timer():
    """The user timer of the periodic check; the package enables it, but it only starts at the next login."""
    try:
        subprocess.run(["systemctl", "--user", "start", "catholic-background-gtk-update.timer"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        pass


class Updater:
    def __init__(self, settings=None):
        self.settings = settings or Settings()

    def wallpaper_day(self):
        try:
            return datetime.date.fromisoformat(self.settings["show_date"])
        except ValueError:
            return datetime.date.today()

    def _record(self, ok, message):
        self.settings["last_check"] = datetime.datetime.now().isoformat(timespec="minutes")
        self.settings["last_result"] = message
        self.settings.save()
        return ok, message

    def due(self):
        """Whether the interval since the last check has passed (the timer runs more often)."""
        try:
            last = datetime.datetime.fromisoformat(self.settings["last_check"])
        except ValueError:
            return True
        return datetime.datetime.now() - last >= datetime.timedelta(minutes=max(5, int(self.settings["interval"])) - 1)

    def check(self, force=False, automatic=False):
        """
        Puts the image of the day if it changed (or always with force). An automatic check goes
        back to today after a day chosen with "Use as wallpaper". Returns (ok, message).
        """
        s = self.settings
        if not s["wallpaper"]:
            return True, "The image of the day is not the desktop background (see the preferences)."
        if automatic:
            s["show_date"] = ""
        day = self.wallpaper_day()
        try:
            url = request_url(s["server"], day, s.language_code(), s["label"])
            artwork = fetch(url)
        except ServerError as error:
            return self._record(False, str(error))
        width, height, top = (list(s["screen"]) + [1920, 1080, 0])[:3]
        composed = json.dumps([artwork["hash"], width, height, top, s["background"], s["color"], s["lock_screen"]])
        current = self._current_file()
        if not force and composed == s["composed"] and current and os.path.exists(current):
            return self._record(True, "The image has not changed.")
        try:
            data = composer.compose(artwork["bytes"], int(width), int(height), s["background"], s["color"], int(top))
        except (OSError, ValueError) as error:
            return self._record(False, f"The image could not be composed: {error}")
        new = self._write(data, composed)
        if not automatic:
            start_timer()
        remember_previous(DESKTOP)
        _set_picture(DESKTOP, GLib.filename_to_uri(new))
        if s["lock_screen"]:
            remember_previous(LOCK)
            _set_picture(LOCK, GLib.filename_to_uri(new))
        changed = bool(s["image_hash"]) and artwork["hash"] != s["image_hash"]
        s.update(image_hash=artwork["hash"], composed=composed, reason=artwork["reason"],
                 title=title_with_year(artwork), author=artwork["author"])
        if changed and automatic and s["notify"]:
            notify(artwork)
        return self._record(True, "The wallpaper has been updated.")

    def _current_file(self):
        files = sorted(glob.glob(os.path.join(data_dir(), "wallpaper-*.jpg")), key=os.path.getmtime)
        return files[-1] if files else ""

    def _write(self, data, key):
        """A new file name each time, so that GNOME notices the change; the old ones are removed."""
        os.makedirs(data_dir(), exist_ok=True)
        name = os.path.join(data_dir(), f"wallpaper-{hashlib.sha1(key.encode()).hexdigest()[:12]}.jpg")
        temporary = name + ".tmp"
        with open(temporary, "wb") as f:
            f.write(data)
        os.replace(temporary, name)
        for old in glob.glob(os.path.join(data_dir(), "wallpaper-*.jpg")):
            if old != name:
                os.remove(old)
        return name

    def set_lock_screen(self, enabled):
        """The lock screen option: the image now, or the previous background back."""
        self.settings["lock_screen"] = enabled
        self.settings.save()
        current = self._current_file()
        if enabled and current and self.settings["wallpaper"]:
            remember_previous(LOCK)
            _set_picture(LOCK, GLib.filename_to_uri(current))
        elif not enabled:
            restore_previous(LOCK)

    def stop(self):
        """The wallpaper option turned off: the previous backgrounds back."""
        restore_previous(DESKTOP)
        restore_previous(LOCK)


def notify(artwork):
    """GNOME notification of a new image; clicking it opens the application (D-Bus activation)."""
    application = Gio.Application(application_id=APP_ID, flags=Gio.ApplicationFlags.NON_UNIQUE)
    try:
        application.register(None)
    except GLib.Error:
        return
    notification = Gio.Notification.new(artwork["reason"] or "New image of the day")
    body = " — ".join(t for t in (title_with_year(artwork), artwork["author"]) if t)
    notification.set_body(body or "The wallpaper has changed.")
    notification.set_default_action("app.open")
    application.send_notification("new-image", notification)
