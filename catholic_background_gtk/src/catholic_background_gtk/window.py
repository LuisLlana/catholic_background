# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Main window: the image of any day with all its data, like the other applications."""

import datetime
import threading

from gi.repository import Adw, Gdk, GLib, Gtk

from . import server
from .wallpaper import Updater


def in_background(work, done):
    """work() in another thread (network, images); done(result, error) back in the interface."""
    def run():
        try:
            result, error = work(), None
        except Exception as problem:        # shown to the user, never lost
            result, error = None, problem
        GLib.idle_add(lambda: done(result, error) and False)
    threading.Thread(target=run, daemon=True).start()


def long_date(day):
    return day.strftime("%A, %d %B %Y").replace(" 0", " ")


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, application, settings):
        super().__init__(application=application, title="Catholic Background", default_width=980, default_height=860)
        self.settings = settings
        self.updater = Updater(settings)
        self.view_day = datetime.date.today()
        self.artwork = None
        self.alternative = False        # the artwork shown came with "Next image"
        self.request = 0

        self.toasts = Adw.ToastOverlay()
        view = Adw.ToolbarView()
        self.toasts.set_child(view)
        self.set_content(self.toasts)

        header = Adw.HeaderBar()
        self.window_title = Adw.WindowTitle(title="Catholic Background")
        header.set_title_widget(self.window_title)
        menu = Gtk.MenuButton(icon_name="open-menu-symbolic", tooltip_text="Menu")
        model = Gio_menu([("Preferences", "app.preferences"), ("About Catholic Background", "app.about"),
                          ("Quit", "app.quit")])
        menu.set_menu_model(model)
        header.pack_end(menu)
        self.refresh_button = Gtk.Button(icon_name="view-refresh-symbolic", tooltip_text="Refresh wallpaper")
        self.refresh_button.connect("clicked", lambda *_: self.refresh_wallpaper())
        header.pack_start(self.refresh_button)
        view.add_top_bar(header)

        # First time: offer to use the image as the desktop background
        self.banner = Adw.Banner(title="Put the image of the day as the desktop background?",
                                 button_label="Use it", revealed=not settings["wallpaper"])
        self.banner.connect("button-clicked", lambda *_: self.turn_wallpaper_on())
        view.add_top_bar(self.banner)

        scroller = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        clamp = Adw.Clamp(maximum_size=920, tightening_threshold=700)
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                       margin_top=12, margin_bottom=24, margin_start=16, margin_end=16)
        clamp.set_child(page)
        scroller.set_child(clamp)
        view.set_content(scroller)

        # ---- the day
        days = Gtk.Box(spacing=6)
        previous = Gtk.Button(icon_name="go-previous-symbolic", tooltip_text="Previous day")
        previous.connect("clicked", lambda *_: self.load(self.view_day - datetime.timedelta(days=1)))
        self.calendar = Gtk.Calendar()
        self.calendar.connect("day-selected", self.on_calendar)
        popover = Gtk.Popover(child=self.calendar)
        self.date_button = Gtk.MenuButton(popover=popover, tooltip_text="Choose the day")
        following = Gtk.Button(icon_name="go-next-symbolic", tooltip_text="Next day")
        following.connect("clicked", lambda *_: self.load(self.view_day + datetime.timedelta(days=1)))
        self.today_button = Gtk.Button(label="Today")
        self.today_button.connect("clicked", lambda *_: self.load(datetime.date.today()))
        self.spinner = Gtk.Spinner()
        for widget in (previous, self.date_button, following, self.today_button):
            days.append(widget)
        days.append(Gtk.Box(hexpand=True))
        days.append(self.spinner)
        page.append(days)

        # ---- the image
        self.picture = Gtk.Picture(content_fit=Gtk.ContentFit.CONTAIN, can_shrink=True, height_request=440)
        self.picture.add_css_class("card")
        page.append(self.picture)
        self.message = Gtk.Label(wrap=True, visible=False, css_classes=["dim-label"])
        page.append(self.message)

        # ---- other artworks of the same day (only to see them)
        others = Gtk.Box(spacing=12)
        self.position = Gtk.Label(css_classes=["dim-label"])
        self.next_image = Gtk.Button(label="Next image", tooltip_text="Another image of the same day (only to see it)")
        self.next_image.connect("clicked", lambda *_: self.show_next())
        others.append(self.position)
        others.append(self.next_image)
        self.others = others
        page.append(others)
        self.alternative_note = Gtk.Label(wrap=True, xalign=0, css_classes=["dim-label", "caption"],
                                          label="Use as Wallpaper puts the image of the current turn of the day, "
                                                "which may not be this one.")
        page.append(self.alternative_note)

        # ---- actions
        actions = Gtk.Box(spacing=8)
        self.use_button = Gtk.Button(label="Use as Wallpaper", css_classes=["suggested-action", "pill"])
        self.use_button.connect("clicked", lambda *_: self.use_as_wallpaper())
        self.edit_button = Gtk.LinkButton(label="Edit this image")
        actions.append(self.use_button)
        actions.append(self.edit_button)
        page.append(actions)
        self.note = Gtk.Label(wrap=True, xalign=0, css_classes=["dim-label"])
        page.append(self.note)

        # ---- texts
        self.reason = Gtk.Label(wrap=True, xalign=0, selectable=True, css_classes=["heading", "accent"])
        self.title_label = Gtk.Label(wrap=True, xalign=0, selectable=True, css_classes=["title-1"])
        self.author = Gtk.Label(wrap=True, xalign=0, selectable=True, css_classes=["title-4"])
        self.description = Gtk.Label(wrap=True, xalign=0, selectable=True)
        # Texts translated by LibreTranslate: say so and give the credit, with its link
        self.machine = Gtk.Label(wrap=True, xalign=0, use_markup=True, css_classes=["dim-label", "caption"])
        self.details = Adw.PreferencesGroup()
        for widget in (self.machine, self.reason, self.title_label, self.author, self.description, self.details):
            page.append(widget)
        self.detail_rows = []

        self.status = Gtk.Label(wrap=True, xalign=0, css_classes=["dim-label", "caption"], margin_top=12)
        page.append(self.status)

        self.load(self.view_day)
        self.update_status()

    # ---------------------------------------------------------------- the day
    def on_calendar(self, calendar):
        selected = calendar.get_date()
        day = datetime.date(selected.get_year(), selected.get_month(), selected.get_day_of_month())
        self.date_button.get_popover().popdown()
        if day != self.view_day:
            self.load(day)

    def show_next(self):
        if self.artwork and self.artwork["count"] > 1:
            self.load(self.view_day, after=self.artwork["id"])

    def load(self, day, after=None):
        self.request += 1
        number = self.request
        self.view_day = day
        self.alternative = after is not None
        self.artwork = None
        self.date_button.set_label(long_date(day))
        self.window_title.set_subtitle(long_date(day))
        self.today_button.set_sensitive(day != datetime.date.today())
        self.calendar.select_day(GLib.DateTime.new_local(day.year, day.month, day.day, 12, 0, 0))
        self.spinner.start()
        s = self.settings
        url = server.request_url(s["server"], day, s.language_code(), label=False, next_id=after)

        def done(artwork, error):
            if number != self.request:
                return
            self.spinner.stop()
            if error:
                self.show_problem(str(error))
            else:
                self.show_artwork(artwork)
        in_background(lambda: server.fetch(url), done)
        self.update_view()

    def show_problem(self, text):
        self.picture.set_paintable(None)
        self.message.set_label(text)
        self.message.set_visible(True)
        self.update_view()

    def show_artwork(self, artwork):
        self.artwork = artwork
        self.message.set_visible(False)
        try:
            self.picture.set_paintable(Gdk.Texture.new_from_bytes(GLib.Bytes.new(artwork["bytes"])))
        except GLib.Error:
            self.show_problem("The server did not send a valid image.")
            return
        self.update_view()

    def update_view(self):
        artwork = self.artwork or {}
        self.reason.set_label(artwork.get("reason", ""))
        self.title_label.set_label(artwork.get("title", "") or ("Untitled" if artwork else ""))
        self.author.set_label(", ".join(t for t in (artwork.get("author", ""), artwork.get("year", "")) if t))
        self.description.set_label(artwork.get("description", ""))
        for widget in (self.reason, self.title_label, self.author, self.description):
            widget.set_visible(bool(widget.get_label()))
        machine = artwork.get("machine")
        self.machine.set_visible(bool(machine))
        if machine:
            notice = GLib.markup_escape_text(machine["notice"])
            url = machine["url"]
            self.machine.set_markup(f'{notice} · <a href="{GLib.markup_escape_text(url)}">'
                                    f'{GLib.markup_escape_text(server.link_label(url))}</a>'
                                    if server.is_web_link(url) else notice)
        for row in self.detail_rows:
            self.details.remove(row)
        self.detail_rows = []
        rows = list(artwork.get("extra", []))
        if artwork.get("license"):
            rows.append(("License", artwork["license"]))
        for name, value in rows:
            row = Adw.ActionRow(title=name, subtitle=value, subtitle_selectable=True)
            row.add_css_class("property")
            self.details.add(row)
            self.detail_rows.append(row)
        if artwork.get("source"):
            row = Adw.ActionRow(title="Source", subtitle=artwork["source"], subtitle_selectable=True)
            row.add_css_class("property")
            if server.is_web_link(artwork["source"]):
                link = Gtk.Button(icon_name="adw-external-link-symbolic", valign=Gtk.Align.CENTER,
                                  css_classes=["flat"], tooltip_text="Open")
                link.connect("clicked", lambda *_, url=artwork["source"]: Gtk.UriLauncher(uri=url).launch(self, None, None))
                row.add_suffix(link)
            self.details.add(row)
            self.detail_rows.append(row)
        self.details.set_visible(bool(self.detail_rows))

        several = artwork.get("count", 0) > 1
        self.others.set_visible(several)
        if several:
            self.position.set_label(f"Image {artwork['position']} of {artwork['count']} of this day")
        self.alternative_note.set_visible(several and self.alternative)
        edit = artwork.get("edit_url", "")
        self.edit_button.set_visible(server.is_web_link(edit))
        if edit:
            self.edit_button.set_uri(edit)
        is_wallpaper = self.settings["wallpaper"] and self.view_day == self.updater.wallpaper_day()
        self.use_button.set_sensitive(bool(artwork) and not is_wallpaper)
        self.use_button.set_label("This Is Your Wallpaper" if is_wallpaper and artwork else "Use as Wallpaper")
        wallpaper_day = self.updater.wallpaper_day()
        self.note.set_visible(self.settings["wallpaper"] and wallpaper_day != datetime.date.today())
        self.note.set_label(f"The wallpaper shows the image of {long_date(wallpaper_day)} until the next "
                            "automatic check, which returns to today.")

    # ---------------------------------------------------------------- the wallpaper
    def turn_wallpaper_on(self):
        self.settings["wallpaper"] = True
        self.settings.save()
        self.banner.set_revealed(False)
        self.refresh_wallpaper()

    def use_as_wallpaper(self):
        self.settings["wallpaper"] = True
        self.banner.set_revealed(False)
        self.settings["show_date"] = "" if self.view_day == datetime.date.today() else self.view_day.isoformat()
        self.settings.save()
        self.refresh_wallpaper()

    def refresh_wallpaper(self):
        if not self.settings["wallpaper"]:
            self.toast("Turn on the desktop background in the preferences first.")
            return
        self.refresh_button.set_sensitive(False)
        self.use_button.set_sensitive(False)

        def done(result, error):
            self.refresh_button.set_sensitive(True)
            ok, message = result if result else (False, str(error))
            self.toast(message)
            self.update_status()
            self.update_view()
        in_background(lambda: self.updater.check(force=True), done)

    def update_status(self):
        s = self.settings
        if not s["wallpaper"]:
            self.status.set_label("The image of the day is not the desktop background.")
            return
        when = s["last_check"].replace("T", " ") if s["last_check"] else "never"
        self.status.set_label(f"Last check: {when}. {s['last_result']}")

    def toast(self, text):
        if text:
            self.toasts.add_toast(Adw.Toast(title=GLib.markup_escape_text(text), timeout=4))


def Gio_menu(items):
    from gi.repository import Gio
    menu = Gio.Menu()
    for label, action in items:
        menu.append(label, action)
    return menu
