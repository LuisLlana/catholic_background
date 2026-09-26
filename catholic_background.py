# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Catholic background of the day: download today's image and set it as wallpaper.

    import catholic_background
    catholic_background.set_wallpaper()                       # simba server, blurred background
    catholic_background.set_wallpaper(background="average")   # average color of the image
    catholic_background.set_wallpaper(background="#1f3a5f")   # a color

Works on Windows, macOS, GNOME and KDE Plasma. Requires Pillow (pip install Pillow certifi).

The image is shown complete and as big as possible on the primary screen; the
rest of the screen is filled with a blurred copy of it, its average color or a
color.

Server protocol:
    GET <server>?ts=<Unix timestamp of today's local midnight>
    -> {"image": "<base64>", "title": ..., "author": ..., "date": ...}
"""

import base64
import datetime
import io
import json
import os
import platform
import re
import shutil
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps, ImageStat

DEFAULT_SERVER = "https://simba.fdi.ucm.es/background"
DEFAULT_BACKGROUND = "blur"

__all__ = ["set_wallpaper", "DEFAULT_SERVER", "DEFAULT_BACKGROUND"]


def set_wallpaper(server=DEFAULT_SERVER, background=DEFAULT_BACKGROUND):
    """
    Downloads today's image from `server` and sets it as the wallpaper.

    `background` fills the screen around the image: "blur" (default), "average"
    (average color of the image) or a color such as "#1f3a5f".

    Returns a dict with "title", "author" and "file" (the composed wallpaper).
    Raises RuntimeError with a readable message if something fails.
    """
    data = _download(server)
    image = ImageOps.exif_transpose(Image.open(io.BytesIO(data["image"]))).convert("RGB")

    size = _screen_size()
    wallpaper, fill = _compose(image, size, background)
    path = _save(wallpaper)
    _apply(path, fill)

    return {"title": data["title"], "author": data["author"], "file": str(path)}


# ---------------------------------------------------------------- server

def _download(server):
    parts = urllib.parse.urlsplit(server.strip())
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise RuntimeError("The server URL must start with http:// or https://")

    midnight = datetime.datetime.combine(datetime.date.today(), datetime.time())
    query = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query) if k != "ts"]
    query.append(("ts", str(int(midnight.timestamp()))))
    url = urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(query)))

    try:
        with urllib.request.urlopen(url, timeout=60, context=_ssl_context()) as response:
            answer = json.load(response)
    except OSError as e:
        raise RuntimeError(f"Could not connect to the server: {e}") from e
    except ValueError as e:
        raise RuntimeError("The server did not answer with JSON") from e

    if not isinstance(answer, dict) or not isinstance(answer.get("image"), str):
        raise RuntimeError('The answer of the server has no "image" field')
    encoded = answer["image"]
    if encoded.startswith("data:"):
        encoded = encoded.split(",", 1)[1]
    try:
        image = base64.b64decode(encoded, validate=True)
    except ValueError as e:
        raise RuntimeError('The "image" field is not valid base64') from e

    title = str(answer.get("title") or "").strip()
    date = str(answer.get("date") or "").strip()
    return {
        "image": image,
        "title": f"{title} ({date})" if title and date else title or date,
        "author": str(answer.get("author") or "").strip(),
    }


def _ssl_context():
    """Uses certifi's certificates when available (python.org builds on macOS need them)."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


# ---------------------------------------------------------------- composition

def _compose(image, size, background):
    """The whole image, as big as possible, centered on the chosen background."""
    width, height = size
    if background == "blur":
        fill = _average(image)
        canvas = _blurred(image, size)
    elif background == "average":
        fill = _average(image)
        canvas = Image.new("RGB", size, fill)
    else:
        fill = _parse_color(background)
        canvas = Image.new("RGB", size, fill)

    scale = min(width / image.width, height / image.height)
    fitted = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))),
                          Image.LANCZOS)
    canvas.paste(fitted, ((width - fitted.width) // 2, (height - fitted.height) // 2))
    return canvas, fill


def _blurred(image, size):
    """The image enlarged to cover the screen, blurred and slightly darkened."""
    cover = ImageOps.fit(image, size, Image.LANCZOS)
    small = cover.resize((64, max(1, round(64 * size[1] / size[0]))), Image.LANCZOS)
    small = small.filter(ImageFilter.GaussianBlur(4)).point(lambda v: int(v * 0.73))
    return small.resize(size, Image.BICUBIC)


def _average(image):
    return tuple(int(v) for v in ImageStat.Stat(image.resize((64, 64))).mean[:3])


def _parse_color(text):
    match = re.fullmatch(r"#?([0-9a-fA-F]{6})", str(text).strip())
    if not match:
        raise RuntimeError(f'Unknown background "{text}": use "blur", "average" or a color like "#1f3a5f"')
    value = match.group(1)
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def _save(wallpaper):
    """Saves with a new name every time (desktops cache wallpapers by file name)."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir()))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "backgrounds"
    folder = base / "catholic-background-python"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{int(time.time() * 1000)}.jpg"
    wallpaper.save(path, "JPEG", quality=92)
    for old in folder.glob("*.jpg"):
        if old != path:
            try:
                old.unlink()
            except OSError:
                pass
    return path


# ---------------------------------------------------------------- screen size

def _screen_size():
    """Size of the primary screen in pixels (only its proportions really matter)."""
    if sys.platform == "win32":
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)   # physical pixels
        except (AttributeError, OSError):
            pass
        user32 = ctypes.windll.user32
        return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

    if sys.platform == "darwin":
        size = _macos_screen_size()
        if size:
            return size

    # X11 and XWayland: primary output of xrandr
    if shutil.which("xrandr"):
        try:
            output = subprocess.run(["xrandr", "--current"], capture_output=True, text=True, timeout=10).stdout
            lines = [line for line in output.splitlines() if " connected" in line]
            lines.sort(key=lambda line: " primary " not in line)
            for line in lines:
                match = re.search(r"(\d+)x(\d+)\+\d+\+\d+", line)
                if match:
                    return int(match.group(1)), int(match.group(2))
        except (OSError, subprocess.SubprocessError):
            pass

    try:
        import tkinter
        root = tkinter.Tk()
        root.withdraw()
        size = root.winfo_screenwidth(), root.winfo_screenheight()
        root.destroy()
        return size
    except Exception:
        return 1920, 1080


def _macos_screen_size():
    """Pixel size of the main display, from system_profiler."""
    try:
        output = subprocess.run(["system_profiler", "SPDisplaysDataType", "-json"],
                                capture_output=True, text=True, timeout=30).stdout
        displays = [d for gpu in json.loads(output).get("SPDisplaysDataType", [])
                    for d in gpu.get("spdisplays_ndrvs", [])]
        displays.sort(key=lambda d: d.get("spdisplays_main") != "spdisplays_yes")
        for display in displays:
            for key in ("_spdisplays_pixels", "_spdisplays_resolution"):
                match = re.search(r"(\d+)\s*x\s*(\d+)", str(display.get(key, "")))
                if match:
                    return int(match.group(1)), int(match.group(2))
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return None


# ---------------------------------------------------------------- desktops

def _apply(path, fill):
    if sys.platform == "win32":
        _apply_windows(path)
        return
    if sys.platform == "darwin":
        _apply_macos(path)
        return
    desktop = (os.environ.get("XDG_CURRENT_DESKTOP", "") + ":" + os.environ.get("DESKTOP_SESSION", "")).lower()
    if "kde" in desktop or "plasma" in desktop:
        _apply_kde(path)
    elif any(name in desktop for name in ("gnome", "unity", "budgie", "pantheon")):
        _apply_gnome(path, fill)
    else:
        raise RuntimeError(f"Unsupported desktop ({platform.system()}, {desktop.strip(':') or 'unknown'}): "
                           "Windows, macOS, GNOME and KDE Plasma are supported")


def _apply_windows(path):
    import ctypes
    import winreg
    # Style "Fit": the composed image already has the size of the screen
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop", 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, "WallpaperStyle", 0, winreg.REG_SZ, "6")
        winreg.SetValueEx(key, "TileWallpaper", 0, winreg.REG_SZ, "0")
    SPI_SETDESKWALLPAPER, SPIF_UPDATEINIFILE, SPIF_SENDCHANGE = 20, 0x01, 0x02
    if not ctypes.windll.user32.SystemParametersInfoW(SPI_SETDESKWALLPAPER, 0, str(path),
                                                      SPIF_UPDATEINIFILE | SPIF_SENDCHANGE):
        raise RuntimeError("Windows did not accept the wallpaper")


def _apply_macos(path):
    # The first time, macOS asks for permission to control "System Events".
    # It changes the picture of every display (on the current Space of each one).
    script = ('tell application "System Events" to tell every desktop to set picture to POSIX file "%s"'
              % str(path).replace("\\", "\\\\").replace('"', '\\"'))
    _run(["osascript", "-e", script])


def _apply_gnome(path, fill):
    uri = Path(path).as_uri()
    color = "#%02x%02x%02x" % fill
    for key, value in (("picture-options", "scaled"), ("primary-color", color),
                       ("color-shading-type", "solid"), ("picture-uri", uri), ("picture-uri-dark", uri)):
        _run(["gsettings", "set", "org.gnome.desktop.background", key, value])


def _apply_kde(path):
    uri = Path(path).as_uri()
    script = (
        "desktops().forEach(function (d) {"
        '  d.wallpaperPlugin = "org.kde.image";'
        '  d.currentConfigGroup = ["Wallpaper", "org.kde.image", "General"];'
        f'  d.writeConfig("Image", "{uri}");'
        '  d.writeConfig("FillMode", 1);'   # Image.PreserveAspectFit: always complete
        "});"
    )
    for qdbus in ("qdbus6", "qdbus", "qdbus-qt6"):
        if shutil.which(qdbus):
            _run([qdbus, "org.kde.plasmashell", "/PlasmaShell", "org.kde.PlasmaShell.evaluateScript", script])
            return
    if shutil.which("plasma-apply-wallpaperimage"):
        _run(["plasma-apply-wallpaperimage", str(path)])
        return
    raise RuntimeError("Could not find qdbus6 or plasma-apply-wallpaperimage to talk to Plasma")


def _run(command):
    try:
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=30)
    except FileNotFoundError as e:
        raise RuntimeError(f"{command[0]} is not installed") from e
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"{command[0]} failed: {(e.stderr or e.stdout).strip()}") from e


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Set today's Catholic background as wallpaper.")
    parser.add_argument("--server", default=DEFAULT_SERVER, help=f"server URL (default: {DEFAULT_SERVER})")
    parser.add_argument("--background", default=DEFAULT_BACKGROUND,
                        help='"blur" (default), "average" or a color like "#1f3a5f"')
    args = parser.parse_args()
    try:
        result = set_wallpaper(args.server, args.background)
    except RuntimeError as e:
        sys.exit(f"Error: {e}")
    print(" — ".join(filter(None, (result["title"], result["author"]))) or "Wallpaper set")
