# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
catholic-background-gtk                 the window
catholic-background-gtk --update        periodic check (systemd user timer): new image, if any
catholic-background-gtk --refresh       put the image of the day now
"""

import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio  # noqa: E402

from . import VERSION  # noqa: E402
from .config import APP_ID, Settings  # noqa: E402
from .wallpaper import Updater, detect_screen  # noqa: E402


class Application(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.settings = None
        self.window = None
        for name, callback in (("open", lambda *_: self.activate()), ("preferences", self.on_preferences),
                               ("about", self.on_about), ("quit", lambda *_: self.quit())):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            self.add_action(action)
        self.set_accels_for_action("app.quit", ["<Control>q"])
        self.set_accels_for_action("app.preferences", ["<Control>comma"])

    def do_activate(self):
        if self.window is None:
            from .window import MainWindow
            self.settings = Settings()
            detect_screen(self.settings)        # the composition fits the screen
            self.settings.save()
            self.window = MainWindow(self, self.settings)
        self.window.present()

    def on_preferences(self, *_):
        self.activate()
        from .preferences import Preferences
        Preferences(self.window).present(self.window)

    def on_about(self, *_):
        self.activate()
        about = Adw.AboutDialog(application_name="Catholic Background", application_icon=APP_ID, version=VERSION,
                                developer_name="Luis Llana", license_type=__import__("gi").repository.Gtk.License.GPL_3_0,
                                comments="A work of Catholic sacred art as the background of the desktop, the lock "
                                         "screen and the login screen, every day.",
                                website="https://simba.fdi.ucm.es/background/browser/")
        about.present(self.window)


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    if "--update" in argv or "--refresh" in argv:
        settings = Settings()
        detect_screen(settings)
        updater = Updater(settings)
        if "--update" in argv and not updater.due():
            return 0
        ok, message = updater.check(force="--refresh" in argv, automatic="--update" in argv)
        print(message)
        return 0 if ok else 1
    return Application().run(argv)
