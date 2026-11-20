# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Preferences: where the image goes (desktop, lock screen, login screen), how it looks, the server."""

from gi.repository import Adw, Gdk, Gio, Gtk

from . import login, server
from .window import in_background

BACKGROUNDS = [("blur", "Blurred image"), ("average", "Average color of the image"), ("color", "A color")]


class Preferences(Adw.PreferencesDialog):
    def __init__(self, window):
        super().__init__(title="Preferences", search_enabled=False)
        self.window = window
        self.settings = window.settings
        s = self.settings
        page = Adw.PreferencesPage()
        self.add(page)

        # ---- where the image goes
        where = Adw.PreferencesGroup(title="Image of the Day")
        page.add(where)
        self.wallpaper = Adw.SwitchRow(title="Desktop background", active=s["wallpaper"],
                                       subtitle="Changes by itself when there is a new image")
        self.wallpaper.connect("notify::active", self.on_wallpaper)
        where.add(self.wallpaper)
        self.lock = Adw.SwitchRow(title="Lock screen", active=s["lock_screen"],
                                  subtitle="GNOME 42 or later always shows the desktop background, blurred, "
                                           "on the lock screen; this sets its own picture too (older GNOME)")
        self.lock.connect("notify::active", self.on_lock)
        where.add(self.lock)
        self.login = Adw.SwitchRow(title="Login screen", subtitle="Looking for the login screen…", sensitive=False)
        self.login_handler = self.login.connect("notify::active", self.on_login)
        where.add(self.login)
        self.notify_row = Adw.SwitchRow(title="Notify when the image changes", active=s["notify"])
        self.notify_row.connect("notify::active", lambda row, _: self.save(notify=row.get_active()))
        where.add(self.notify_row)
        interval = Adw.SpinRow.new_with_range(5, 1440, 5)
        interval.set_title("Check every (minutes)")
        interval.set_value(s["interval"])
        interval.connect("notify::value", lambda row, _: self.save(interval=int(row.get_value())))
        where.add(interval)
        in_background(login.status, self.show_login_status)

        # ---- how it looks
        looks = Adw.PreferencesGroup(title="Around the Image",
                                     description="The image is always shown whole and as big as possible.")
        page.add(looks)
        label = Adw.SwitchRow(title="Label", subtitle="The reason, title and author below the artwork",
                              active=s["label"])
        label.connect("notify::active", lambda row, _: self.save(recompose=True, label=row.get_active()))
        looks.add(label)
        self.background = Adw.ComboRow(title="Rest of the screen", model=Gtk.StringList.new([n for _, n in BACKGROUNDS]))
        self.background.set_selected([k for k, _ in BACKGROUNDS].index(s["background"]) if s["background"] in
                                     dict(BACKGROUNDS) else 0)
        self.background.connect("notify::selected", self.on_background)
        looks.add(self.background)
        self.color_row = Adw.ActionRow(title="Color")
        color = Gdk.RGBA()
        color.parse(s["color"])
        self.color_button = Gtk.ColorDialogButton(dialog=Gtk.ColorDialog(with_alpha=False), rgba=color,
                                                  valign=Gtk.Align.CENTER)
        self.color_button.connect("notify::rgba", self.on_color)
        self.color_row.add_suffix(self.color_button)
        self.color_row.set_visible(s["background"] == "color")
        looks.add(self.color_row)

        # ---- server and language
        source = Adw.PreferencesGroup(title="Server")
        page.add(source)
        self.url = Adw.EntryRow(title="Address", text=s["server"], show_apply_button=True)
        self.url.connect("apply", self.on_url)
        source.add(self.url)
        buttons = Adw.ActionRow(title="Default server", subtitle=server.DEFAULT_SERVER)
        default = Gtk.Button(label="Use", valign=Gtk.Align.CENTER)
        default.connect("clicked", lambda *_: (self.url.set_text(server.DEFAULT_SERVER), self.on_url(self.url)))
        buttons.add_suffix(default)
        source.add(buttons)
        self.languages = [("", "Language of the system")]
        self.people = 1             # entries of the first part of the menu (the others: machine translation)
        self.language = Adw.ComboRow(title="Language of the texts", model=Gtk.StringList.new([self.languages[0][1]]))
        self.language_handler = self.language.connect("notify::selected", self.on_language)
        source.add(self.language)
        self.load_languages()

    # ---------------------------------------------------------------- saving
    def save(self, recompose=False, **values):
        changed = any(self.settings.get(k) != v for k, v in values.items())
        self.settings.update(values)
        self.settings.save()
        if changed and recompose:
            if self.settings["wallpaper"]:
                self.window.refresh_wallpaper()
            self.window.load(self.window.view_day)
            if self.login.get_active():
                self.window.toast("The login screen keeps the settings it had: turn it off and on to use these.")

    def on_wallpaper(self, row, _):
        on = row.get_active()
        self.save(wallpaper=on)
        self.window.banner.set_revealed(not on)
        if on:
            self.window.refresh_wallpaper()
        else:
            self.window.updater.stop()
        self.window.update_status()
        self.window.update_view()

    def on_lock(self, row, _):
        self.window.updater.set_lock_screen(row.get_active())

    def on_background(self, row, _):
        key = BACKGROUNDS[row.get_selected()][0]
        self.color_row.set_visible(key == "color")
        self.save(recompose=True, background=key)

    def on_color(self, button, _):
        rgba = button.get_rgba()
        hex_color = "#{:02x}{:02x}{:02x}".format(*(round(c * 255) for c in (rgba.red, rgba.green, rgba.blue)))
        self.save(recompose=self.settings["background"] == "color", color=hex_color)

    def on_url(self, entry):
        try:
            url = server.validate(entry.get_text())
        except server.ServerError as error:
            self.window.toast(str(error))
            return
        self.save(recompose=True, server=url)
        self.load_languages()

    # ---------------------------------------------------------------- languages
    def load_languages(self):
        def done(found, error):
            people, machine = found or ([], [])
            first = [("", "Language of the system")] + people
            self.languages = first + machine
            self.people = len(first)
            self.language.handler_block(self.language_handler)
            # Two parts: the languages translated by people, then those of machine translation
            parts = Gio.ListStore(item_type=Gio.ListModel)
            parts.append(Gtk.StringList.new([name for _, name in first]))
            if machine:
                parts.append(Gtk.StringList.new([name for _, name in machine]))
            self.language.set_model(Gtk.FlattenListModel.new(parts))
            self.language.set_header_factory(self.header_factory() if machine else None)
            codes = [code for code, _ in self.languages]
            self.language.set_selected(codes.index(self.settings["language"]) if self.settings["language"] in codes else 0)
            self.language.handler_unblock(self.language_handler)
        in_background(lambda: server.languages(self.settings["server"]), done)

    def header_factory(self):
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", lambda _, header: header.set_child(
            Gtk.Label(xalign=0, margin_top=6, margin_bottom=3, css_classes=["heading", "dim-label"])))
        factory.connect("bind", lambda _, header: header.get_child().set_label(
            "Machine translation (LibreTranslate)" if header.get_start() >= self.people else "Translated by people"))
        return factory

    def on_language(self, row, _):
        index = row.get_selected()
        if 0 <= index < len(self.languages):
            self.save(recompose=True, language=self.languages[index][0])

    # ---------------------------------------------------------------- login screen
    def show_login_status(self, status, error):
        status = status or {}
        greeters = status.get("greeters", [])
        self.login.handler_block(self.login_handler)
        self.login.set_active(bool(status.get("enabled")))
        self.login.handler_unblock(self.login_handler)
        self.login.set_sensitive(bool(greeters) or bool(status.get("enabled")))
        self.login.set_subtitle(("Asks for the administrator password. " + ", ".join(greeters)) if greeters else
                                "No supported login screen found (SDDM or LightDM with the GTK or Slick greeter)")

    def on_login(self, row, _):
        on = row.get_active()
        row.set_sensitive(False)

        def done(result, error):
            ok, message = result if result else (False, str(error))
            self.window.toast(message)
            in_background(login.status, self.show_login_status)   # the real state, also if it failed
        in_background(lambda: login.enable(self.settings) if on else login.disable(), done)
