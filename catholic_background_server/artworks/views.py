# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
import base64
import time
from datetime import datetime, timezone

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import render
from django.utils import timezone as dj_timezone
from django.utils.translation import get_language
from django.views.decorators.http import require_GET

from .models import AccessLog, Language
from .selection import pick

MAX_TS_DISTANCE = 2 * 86400   # do not answer for days far from today


def requested_language(request):
    """?lang=xx, else the Accept-Language header, else the default language of the content."""
    codes = []
    if request.GET.get("lang"):
        codes.append(request.GET["lang"])
    for part in request.META.get("HTTP_ACCEPT_LANGUAGE", "").split(","):
        code = part.split(";")[0].strip()
        if code and code != "*":
            codes.append(code)
    return Language.best_match(codes) or Language.default()


def client_ip(request):
    if getattr(settings, "TRUST_X_FORWARDED_FOR", False):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


@require_GET
def background(request):
    """
    GET /background?ts=<Unix timestamp of the client's local midnight>[&lang=<language code>]
    -> {"image": base64, "title", "author", "date", "description", "source", "license", "extra", "language"}
    The texts are in the requested language (lang, or Accept-Language), or else in the default one.
    """
    now = time.time()
    raw = request.GET.get("ts")
    if raw is None:
        midnight = dj_timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
        ts = int(midnight.timestamp())
    else:
        try:
            ts = int(raw)
        except ValueError:
            return JsonResponse({"error": "invalid ts"}, status=400)
        if abs(now - ts) > MAX_TS_DISTANCE:
            return JsonResponse({"error": "ts too far from today"}, status=400)

    # Local midnight + 12 h falls on the client's calendar day in UTC
    day = datetime.fromtimestamp(ts + 12 * 3600, tz=timezone.utc).date()
    artwork = pick(day, now - ts)
    if artwork is None:
        return JsonResponse({"error": "no image for this day"}, status=404)

    try:
        with artwork.image.open("rb") as f:
            image = base64.b64encode(f.read()).decode("ascii")
    except (FileNotFoundError, ValueError):
        return JsonResponse({"error": "image file missing"}, status=500)

    AccessLog.objects.create(day=dj_timezone.localdate(), ip=client_ip(request),
                             user_agent=request.META.get("HTTP_USER_AGENT", "")[:300],
                             artwork=artwork)

    language = requested_language(request)
    texts = artwork.texts(language)
    response = JsonResponse({
        "image": image,
        "title": texts["title"],
        "author": texts["author"],
        "date": texts["year"],
        "description": texts["description"],
        "source": artwork.source_url,
        "license": texts["license"],
        "extra": artwork.extra(language),
        "language": texts["language"],
    })
    # Several artworks may share a day: never serve a cached answer
    response["Cache-Control"] = "no-store"
    response["Content-Language"] = texts["language"]
    response["Vary"] = "Accept-Language"
    return response


def privacy(request):
    template = "pages/privacy_es.html" if (get_language() or "").startswith("es") else "pages/privacy.html"
    return render(request, template, {"opts": settings.CATHOLIC_BACKGROUND})


@staff_member_required
def protected_media(request, path):
    """Uploaded images are only visible to editors (the applications get them through /background)."""
    try:
        return FileResponse(open(settings.MEDIA_ROOT / path, "rb"))
    except (FileNotFoundError, IsADirectoryError, ValueError):
        raise Http404
