# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""The login screen option: login-background, run as root with pkexec."""

import json
import os
import subprocess

INSTALLED = "/usr/libexec/catholic-background-gtk/login-background"
SOURCE = os.path.join(os.path.dirname(__file__), "..", "..", "login", "login-background")


def helper():
    return INSTALLED if os.path.exists(INSTALLED) else os.path.abspath(SOURCE)


def status():
    """{"enabled": bool, "greeters": [names], "image": path} (no root needed)."""
    try:
        result = subprocess.run([helper(), "status"], capture_output=True, text=True, timeout=10)
        return json.loads(result.stdout)
    except (OSError, ValueError, subprocess.SubprocessError):
        return {"enabled": False, "greeters": [], "image": ""}


def _run(arguments):
    """pkexec asks for the administrator password; returns (ok, message)."""
    try:
        result = subprocess.run(["pkexec", helper(), *arguments], capture_output=True, text=True, timeout=180)
    except FileNotFoundError:
        return False, "pkexec is not installed."
    except subprocess.SubprocessError as error:
        return False, str(error)
    if result.returncode in (126, 127) and not result.stdout:
        return False, "Authentication was cancelled or failed."
    message = (result.stdout or result.stderr).strip().splitlines()
    return result.returncode == 0, message[-1] if message else ""


def enable(settings):
    width, height, _top = (list(settings["screen"]) + [1920, 1080, 0])[:3]
    return _run(["enable", "--server", settings["server"], "--lang", settings.language_code(),
                 "--label", "1" if settings["label"] else "0", "--size", f"{int(width)}x{int(height)}",
                 "--background", settings["background"], "--color", settings["color"]])


def disable():
    return _run(["disable"])
