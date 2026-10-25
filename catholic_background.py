# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Catholic background of the day: a window with the artwork of the day and its data.

    python catholic_background.py                     # today
    python catholic_background.py --date 2026-12-25   # another day
    python catholic_background.py --lang en           # texts in English

    import catholic_background
    catholic_background.show()                        # the window
    data = catholic_background.fetch()                # only the data (dict)

The same on Windows, macOS and Linux: it does not change the wallpaper. The window
takes most of the screen; the artwork is shown complete and as big as possible on
the left, and on the right why it is shown that day (saint, celebration or
liturgical season), its title, author, year, comment, other data, license and
source. Previous and next day with the buttons or the arrow keys, F11 full screen,
Escape closes.

Requires Pillow with Tk support and tkinter:
    Windows and macOS (python.org):  pip install Pillow
    Debian / Ubuntu:                 sudo apt install python3-tk python3-pil.imagetk

Server protocol:
    GET <server>?ts=<Unix timestamp of the local midnight of the day>&lang=<language>&caption=0
    -> {"image": "<base64>", "title", "author", "date", "description", "reason",
        "extra": {name: value}, "license", "source", "edit_url", ...}
"""

import base64
import datetime
import io
import json
import os
import queue
import re
import ssl
import subprocess
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

from PIL import Image, ImageOps

DEFAULT_SERVER = "https://simba.fdi.ucm.es/background"

__all__ = ["show", "fetch", "DEFAULT_SERVER"]


def fetch(server=DEFAULT_SERVER, day=None, lang=None):
    """
    Downloads the artwork of `day` (a datetime.date; by default today) from `server`,
    without the label (its data come apart). `lang` is the language of the texts
    ("es", "en"…); by default, that of the system.

    Returns a dict with "image" (a PIL image), "title", "author", "year", "description",
    "reason", "extra" (list of (name, value)), "license", "source" and "edit_url".
    Raises RuntimeError with a readable message if something fails.
    """
    day = day or datetime.date.today()
    parts = urllib.parse.urlsplit(server.strip())
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise RuntimeError(_("The server URL must start with http:// or https://"))

    midnight = datetime.datetime.combine(day, datetime.time())
    query = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query) if k not in ("ts", "lang", "caption")]
    query.append(("ts", str(int(midnight.timestamp()))))
    lang = lang or _system_language()
    if lang:
        query.append(("lang", lang))
    query.append(("caption", "0"))
    url = urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(query)))

    try:
        with _open_http(url) as response:
            answer = json.load(response)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise RuntimeError(_("There is no image for this day.")) from e
        raise RuntimeError(_("The server answered with an error (HTTP {code}).").format(code=e.code)) from e
    except OSError as e:
        raise RuntimeError(_("Could not connect to the server: {error}").format(error=e)) from e
    except ValueError as e:
        raise RuntimeError(_("The server did not send a valid image.")) from e

    if not isinstance(answer, dict) or not isinstance(answer.get("image"), str):
        raise RuntimeError(_("The server did not send a valid image."))
    encoded = answer["image"]
    if encoded.startswith("data:"):
        encoded = encoded.split(",", 1)[1]
    try:
        image = Image.open(io.BytesIO(base64.b64decode(encoded, validate=True)))
        image = ImageOps.exif_transpose(image).convert("RGB")
    except (ValueError, OSError) as e:
        raise RuntimeError(_("The server did not send a valid image.")) from e

    def text(name):
        return str(answer.get(name) or "").replace("\r\n", "\n").strip()

    extra = answer.get("extra") if isinstance(answer.get("extra"), dict) else {}
    return {"image": image, "title": text("title"), "author": text("author"), "year": text("date"),
            "description": text("description"), "reason": text("reason"),
            "extra": [(str(k).strip(), str(v).strip()) for k, v in extra.items() if str(v or "").strip()],
            "license": text("license"), "source": text("source"), "edit_url": text("edit_url")}


def _is_web_link(url):
    return urllib.parse.urlsplit(url).scheme.lower() in ("http", "https")


# ---------------------------------------------------------------- texts of the window

_SPANISH = {
    "Catholic Background": "Catholic Background",
    "Today": "Hoy",
    "Previous day": "Día anterior",
    "Next day": "Día siguiente",
    "Loading…": "Cargando…",
    "Untitled": "Sin título",
    "License": "Licencia",
    "Source": "Fuente",
    "Edit this image": "Editar esta imagen",
    "The server URL must start with http:// or https://": "La URL del servidor debe empezar por http:// o https://",
    "There is no image for this day.": "No hay imagen para este día.",
    "The server answered with an error (HTTP {code}).": "El servidor respondió con un error (HTTP {code}).",
    "Could not connect to the server: {error}": "No se pudo conectar con el servidor: {error}",
    "The server did not send a valid image.": "El servidor no envió una imagen válida.",
    "The window needs tkinter: {error}": "La ventana necesita tkinter: {error}",
}


def _(text):
    """Texts of the window in Spanish when the system is in Spanish; English otherwise."""
    return _SPANISH.get(text, text) if (_system_language() or "").startswith("es") else text


def _system_language():
    """Language of the system as a code such as "es" or "pt-br" (None if unknown)."""
    code = None
    if sys.platform == "win32":
        import ctypes
        buffer = ctypes.create_unicode_buffer(85)
        if ctypes.windll.kernel32.GetUserDefaultLocaleName(buffer, len(buffer)):
            code = buffer.value
    elif sys.platform == "darwin":
        try:
            code = subprocess.run(["defaults", "read", "-g", "AppleLocale"], capture_output=True,
                                  text=True, timeout=10).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            code = None
    if not code:
        for name in ("LC_ALL", "LC_MESSAGES", "LANG"):
            if os.environ.get(name) and os.environ[name] not in ("C", "POSIX"):
                code = os.environ[name]
                break
    if not code:
        return None
    code = code.split(".")[0].split("@")[0].replace("_", "-").lower()
    return code if re.fullmatch(r"[a-z]{2,3}(-[a-z0-9]+)?", code) else None


def _open_http(url):
    """
    Opens an http(s) address with an opener that only knows HTTP and HTTPS: unlike
    urllib.request.urlopen, it cannot read local files (file://) or use other schemes.
    """
    if urllib.parse.urlsplit(url).scheme not in ("http", "https"):
        raise RuntimeError("The server URL must start with http:// or https://")
    opener = urllib.request.OpenerDirector()
    for handler in (urllib.request.HTTPHandler(), urllib.request.HTTPSHandler(context=_ssl_context()),
                    urllib.request.HTTPRedirectHandler(), urllib.request.HTTPDefaultErrorHandler(),
                    urllib.request.HTTPErrorProcessor()):
        opener.add_handler(handler)
    return opener.open(url, timeout=60)


def _ssl_context():
    """Uses certifi's certificates when available (python.org builds on macOS need them)."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


# ---------------------------------------------------------------- the window

def show(server=DEFAULT_SERVER, day=None, lang=None):
    """Opens the window with the artwork of `day` (by default today) and waits until it is closed."""
    if sys.platform == "win32":
        try:   # sharp texts and image on screens with scaling
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass
    try:
        import tkinter
    except ImportError as e:
        raise RuntimeError(_("The window needs tkinter: {error}").format(error=e)) from e
    root = tkinter.Tk()
    _Viewer(root, server, day or datetime.date.today(), lang)
    root.mainloop()


class _Viewer:
    PANEL_BACKGROUND = "#faf8f3"
    IMAGE_BACKGROUND = "#1e1e1e"
    REASON_COLOR = "#a8740f"
    LINK_COLOR = "#1a5fb4"

    def __init__(self, root, server, day, lang):
        import tkinter as tk
        from tkinter import font
        self.tk = tk
        self.root, self.server, self.lang = root, server, lang
        self.day = day
        self.data = None
        self.photo = None
        self.request = 0
        self.results = queue.Queue()
        self.resize_job = None

        root.title(_("Catholic Background"))
        # Most of the screen, centered
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        width, height = int(sw * 0.9), int(sh * 0.86)
        root.geometry(f"{width}x{height}+{(sw - width) // 2}+{max(0, (sh - height) // 3)}")
        root.minsize(720, 480)

        base = font.nametofont("TkDefaultFont").actual()
        family, size = base["family"], max(10, abs(base["size"]))
        self.fonts = {
            "reason": font.Font(family=family, size=size + 2, weight="bold"),
            "title": font.Font(family=family, size=size + 10, weight="bold"),
            "author": font.Font(family=family, size=size + 4),
            "body": font.Font(family=family, size=size + 2),
            "label": font.Font(family=family, size=size + 1, weight="bold"),
            "value": font.Font(family=family, size=size + 1),
            "day": font.Font(family=family, size=size + 2, weight="bold"),
        }

        # ---- top bar: the day
        bar = tk.Frame(root, padx=10, pady=6)
        bar.pack(side="top", fill="x")
        tk.Button(bar, text="\u25C0", width=3, command=lambda: self.go(-1)).pack(side="left")
        self.today_button = tk.Button(bar, text=_("Today"), command=self.today)
        self.today_button.pack(side="left", padx=6)
        tk.Button(bar, text="\u25B6", width=3, command=lambda: self.go(1)).pack(side="left")
        self.day_label = tk.Label(bar, font=self.fonts["day"])
        self.day_label.pack(side="left", padx=16)

        # ---- the image on the left and its data on the right, with a movable divider
        panes = tk.PanedWindow(root, orient="horizontal", sashwidth=6, sashrelief="flat", bd=0)
        panes.pack(side="top", fill="both", expand=True)
        self.canvas = tk.Canvas(panes, bg=self.IMAGE_BACKGROUND, highlightthickness=0)
        panel = tk.Frame(panes, bg=self.PANEL_BACKGROUND)
        scroll = tk.Scrollbar(panel)
        scroll.pack(side="right", fill="y")
        self.text = tk.Text(panel, wrap="word", bd=0, highlightthickness=0, padx=22, pady=18,
                            bg=self.PANEL_BACKGROUND, yscrollcommand=scroll.set, cursor="arrow",
                            font=self.fonts["body"], spacing1=2, spacing3=2)
        self.text.pack(side="left", fill="both", expand=True)
        scroll.config(command=self.text.yview)
        panes.add(self.canvas, stretch="always", minsize=320)
        panes.add(panel, stretch="never", width=max(340, int(width * 0.32)), minsize=280)

        t = self.text
        t.tag_configure("reason", font=self.fonts["reason"], foreground=self.REASON_COLOR, spacing3=8)
        t.tag_configure("title", font=self.fonts["title"], spacing3=6)
        t.tag_configure("author", font=self.fonts["author"], spacing3=14)
        t.tag_configure("body", font=self.fonts["body"], spacing3=14, spacing2=3)
        t.tag_configure("label", font=self.fonts["label"])
        t.tag_configure("value", font=self.fonts["value"], lmargin1=0, spacing3=8)
        t.tag_configure("link", foreground=self.LINK_COLOR, underline=True)
        t.tag_configure("message", font=self.fonts["author"], spacing1=30, justify="center")
        t.tag_bind("link", "<Enter>", lambda e: t.config(cursor="hand2"))
        t.tag_bind("link", "<Leave>", lambda e: t.config(cursor="arrow"))
        # Read only, but the texts can be selected and copied
        t.bind("<Key>", lambda e: None if (e.state & 0x4 and e.keysym.lower() in ("c", "a")) else "break")

        self.canvas.bind("<Configure>", self.schedule_redraw)
        root.bind("<Left>", lambda e: self.go(-1))
        root.bind("<Right>", lambda e: self.go(1))
        root.bind("<Home>", lambda e: self.today())
        root.bind("<F11>", lambda e: root.attributes("-fullscreen", not root.attributes("-fullscreen")))
        root.bind("<Escape>", lambda e: root.attributes("-fullscreen", False) if root.attributes("-fullscreen") else root.destroy())

        self.load()
        root.after(100, self.poll)

    # ---- the day
    def go(self, days):
        self.day += datetime.timedelta(days=days)
        self.load()

    def today(self):
        if self.day != datetime.date.today():
            self.day = datetime.date.today()
            self.load()

    def load(self):
        """Downloads the artwork in another thread, so the window does not freeze."""
        self.request += 1
        number, day = self.request, self.day
        self.day_label.config(text=_format_day(day))
        self.today_button.config(state="disabled" if day == datetime.date.today() else "normal")
        self.data = None
        self.redraw()
        self.message(_("Loading…"))

        def work():
            try:
                self.results.put((number, fetch(self.server, day, self.lang)))
            except RuntimeError as e:
                self.results.put((number, str(e)))

        threading.Thread(target=work, daemon=True).start()

    def poll(self):
        try:
            while True:
                number, result = self.results.get_nowait()
                if number != self.request:
                    continue   # an older day, already left
                if isinstance(result, str):
                    self.message(result)
                else:
                    self.data = result
                    self.show_texts()
                    self.redraw()
        except queue.Empty:
            pass
        self.root.after(100, self.poll)

    # ---- the image
    def schedule_redraw(self, event=None):
        if self.resize_job:
            self.root.after_cancel(self.resize_job)
        self.resize_job = self.root.after(120, self.redraw)

    def redraw(self):
        from PIL import ImageTk
        self.resize_job = None
        self.canvas.delete("all")
        if not self.data:
            self.photo = None
            return
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        margin = 16
        image = self.data["image"]
        scale = min((width - 2 * margin) / image.width, (height - 2 * margin) / image.height)
        if scale <= 0:
            return
        size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
        self.photo = ImageTk.PhotoImage(image.resize(size, Image.LANCZOS))
        self.canvas.create_image(width // 2, height // 2, image=self.photo, anchor="center")

    # ---- the texts
    def message(self, text):
        self.text.delete("1.0", "end")
        self.text.insert("end", text, "message")

    def show_texts(self):
        d, t = self.data, self.text
        t.delete("1.0", "end")
        if d["reason"]:
            t.insert("end", d["reason"] + "\n", "reason")
        t.insert("end", (d["title"] or _("Untitled")) + "\n", "title")
        author_year = ", ".join(filter(None, (d["author"], d["year"])))
        if author_year:
            t.insert("end", author_year + "\n", "author")
        if d["description"]:
            t.insert("end", d["description"] + "\n", "body")
        rows = list(d["extra"])
        if d["license"]:
            rows.append((_("License"), d["license"]))
        for name, value in rows:
            t.insert("end", name + "\n", "label")
            t.insert("end", value + "\n", "value")
        if d["source"]:
            t.insert("end", _("Source") + "\n", "label")
            self.insert_link(d["source"], d["source"])
        if d["edit_url"] and _is_web_link(d["edit_url"]):
            t.insert("end", "\n")
            self.insert_link(_("Edit this image"), d["edit_url"])
        t.yview_moveto(0)

    def insert_link(self, text, url):
        if not _is_web_link(url):   # only http(s): never local files or other schemes
            self.text.insert("end", text + "\n", "value")
            return
        tag = f"link-{self.text.index('end')}"
        self.text.insert("end", text, ("value", "link", tag))
        self.text.insert("end", "\n", "value")
        self.text.tag_bind(tag, "<Button-1>", lambda e: webbrowser.open(url))


def _format_day(day):
    """The day written out, in Spanish or English as the window."""
    if (_system_language() or "").startswith("es"):
        months = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
                  "septiembre", "octubre", "noviembre", "diciembre")
        weekdays = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
        return f"{weekdays[day.weekday()].capitalize()}, {day.day} de {months[day.month - 1]} de {day.year}"
    return day.strftime("%A, %d %B %Y").replace(" 0", " ")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Shows the Catholic artwork of the day and its data.")
    parser.add_argument("--server", default=DEFAULT_SERVER, help=f"server URL (default: {DEFAULT_SERVER})")
    parser.add_argument("--lang", help="language of the texts (default: that of the system)")
    parser.add_argument("--date", type=datetime.date.fromisoformat, help="day to show, YYYY-MM-DD (default: today)")
    args = parser.parse_args()
    try:
        show(args.server, args.date, args.lang)
    except RuntimeError as e:
        sys.exit(f"Error: {e}")
