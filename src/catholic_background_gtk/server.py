# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Protocol of the server:

    GET <server>?ts=<Unix timestamp of the local midnight of the day>&lang=<language>[&caption=0][&next=<id>]
    -> {"image": "<base64>", "title", "author", "date", "description", "source", "license",
        "extra": {...}, "language", "reason", "id", "edit_url", "position", "count"}
    GET <server>/languages -> {"default": "es", "languages": [{"code", "name"}, ...]}
"""

import base64
import datetime
import hashlib
import json
import locale
import os
import urllib.error
import urllib.parse
import urllib.request

from . import VERSION

DEFAULT_SERVER = "https://simba.fdi.ucm.es/background"
TIMEOUT = 30


class ServerError(Exception):
    """A problem talking to the server, with a message for the user."""


def system_language():
    """Language of the system ("es", "en"…), or ""."""
    for name in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(name, "").split(":")[0]
        if value and value not in ("C", "POSIX") and not value.startswith("C."):
            return value.split(".")[0].split("_")[0].lower()
    try:
        code = locale.getlocale()[0] or ""
    except ValueError:
        code = ""
    return code.split("_")[0].lower()


def validate(base):
    parts = urllib.parse.urlsplit((base or "").strip())
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise ServerError("The server address must start with http:// or https://")
    return base.strip()


def request_url(base, day, language="", label=True, next_id=None):
    """base?ts=<midnight of day>&lang=…[&caption=0][&next=<id>], keeping other parameters of base."""
    parts = urllib.parse.urlsplit(validate(base))
    query = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query) if k not in ("ts", "lang", "caption", "next")]
    midnight = datetime.datetime.combine(day, datetime.time())
    query.append(("ts", str(int(midnight.timestamp()))))
    if language:
        query.append(("lang", language))
    if not label:
        query.append(("caption", "0"))
    if next_id is not None:
        query.append(("next", str(int(next_id))))
    return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(query)))


def _get(url):
    request = urllib.request.Request(url, headers={"User-Agent": f"catholic-background-gtk/{VERSION}",
                                                   "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            raise ServerError("There is no image for this day.") from error
        raise ServerError(f"The server answered with an error (HTTP {error.code}).") from error
    except (OSError, ValueError) as error:
        raise ServerError(f"Could not connect to the server: {getattr(error, 'reason', error)}") from error


def fetch(url):
    """The artwork of an address made with request_url: a dict with "bytes" (the image) and its data."""
    answer = _get(url)
    if not isinstance(answer, dict) or not isinstance(answer.get("image"), str):
        raise ServerError("The server did not send a valid image.")
    encoded = answer["image"]
    if encoded.startswith("data:"):
        encoded = encoded.split(",", 1)[1]
    try:
        data = base64.b64decode(encoded, validate=True)
    except ValueError as error:
        raise ServerError("The server did not send a valid image.") from error

    def text(name):
        return str(answer.get(name) or "").replace("\r\n", "\n").strip()

    extra = answer.get("extra") if isinstance(answer.get("extra"), dict) else {}

    def number(name):
        value = answer.get(name)
        return value if isinstance(value, int) else 0

    return {
        "bytes": data, "hash": hashlib.sha1(data).hexdigest(),
        "title": text("title"), "author": text("author"), "year": text("date"),
        "description": text("description"), "reason": text("reason"),
        "license": text("license"), "source": text("source"), "edit_url": text("edit_url"),
        "extra": [(str(k).strip(), str(v).strip()) for k, v in extra.items() if str(v or "").strip()],
        "id": number("id"), "position": number("position"), "count": number("count"),
    }


def languages(base):
    """[(code, name)] of the languages of the texts, from the server."""
    parts = urllib.parse.urlsplit(validate(base))
    url = urllib.parse.urlunsplit(parts._replace(path=parts.path.rstrip("/") + "/languages", query=""))
    answer = _get(url)
    return [(str(item.get("code", "")), str(item.get("name", ""))) for item in answer.get("languages", [])
            if item.get("code")]


def title_with_year(artwork):
    title, year = artwork.get("title", ""), artwork.get("year", "")
    if title and year:
        return f"{title} ({year})"
    return title or year


def is_web_link(url):
    return urllib.parse.urlsplit(url or "").scheme.lower() in ("http", "https")
