# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
import base64
import time
from datetime import datetime, timezone

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone as dj_timezone
from django.utils.translation import get_language
from django.views.decorators.http import require_GET

from .caption import labelled_jpeg
from .models import AccessLog, Language
from .selection import pick, reason



def requested_language(request):
    """
    ?lang=xx, else the default language of the content. The Accept-Language header is not
    used on purpose: the image (with its label) must be the same for the same request,
    whatever HTTP library the application uses.
    """
    return Language.best_match([request.GET.get("lang", "")]) or Language.default()


def wants_caption(request):
    value = request.GET.get("caption")
    if value is None:
        return settings.CATHOLIC_BACKGROUND["CAPTION_DEFAULT"]
    return value.lower() not in ("0", "false", "no", "off")


def client_ip(request):
    if getattr(settings, "TRUST_X_FORWARDED_FOR", False):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


@require_GET
def background(request):
    """
    GET /background?ts=<Unix timestamp of the client's local midnight>[&lang=<language code>][&caption=0]
    -> {"image": base64, "title", "author", "date", "description", "source", "license", "extra", "language",
        "reason", "reason_type"}
    "reason" says why the artwork is shown that day (saint, celebration or liturgical season), if it is special.
    "id" and "edit_url" identify the artwork and give the page of the admin site to edit it.
    Any day can be asked for with ts, past or future.
    The texts are in the requested language (lang), or else in the default one. The image has a
    label below the artwork with the reason, title and author (unless caption=0).
    """
    now = time.time()
    raw = request.GET.get("ts")
    if raw is None:
        midnight = dj_timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
        ts = int(midnight.timestamp())
    else:
        try:
            ts = int(raw)
            # Any day can be asked for (past or future). Local midnight + 12 h falls on the
            # client's calendar day in UTC.
            day = datetime.fromtimestamp(ts + 12 * 3600, tz=timezone.utc).date()
        except (ValueError, OverflowError, OSError):
            return JsonResponse({"error": "invalid ts"}, status=400)
    if raw is None:
        day = datetime.fromtimestamp(ts + 12 * 3600, tz=timezone.utc).date()

    # The turn within the day follows the client's current time of day, also for other days
    artwork = pick(day, (now - ts) % 86400)
    if artwork is None:
        return JsonResponse({"error": "no image for this day"}, status=404)

    language = requested_language(request)
    texts = artwork.texts(language)
    why = reason(artwork, day, language)
    try:
        if wants_caption(request):
            data = labelled_jpeg(artwork, texts, why["text"])
        else:
            with artwork.image.open("rb") as f:
                data = f.read()
    except (FileNotFoundError, ValueError, OSError):
        return JsonResponse({"error": "image file missing"}, status=500)
    image = base64.b64encode(data).decode("ascii")

    AccessLog.objects.create(day=dj_timezone.localdate(), ip=client_ip(request),
                             user_agent=request.META.get("HTTP_USER_AGENT", "")[:300],
                             artwork=artwork)

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
        "reason": why["text"],
        "reason_type": why["type"],
        "id": artwork.pk,
        # Page of the admin site to edit the artwork (editors must log in)
        "edit_url": request.build_absolute_uri(reverse("admin:artworks_artwork_change", args=[artwork.pk])),
    })
    # Several artworks may share a day: never serve a cached answer
    response["Cache-Control"] = "no-store"
    response["Content-Language"] = texts["language"]
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


@require_GET
def languages(request):
    """Languages of the content, for the language selector of the applications."""
    default = Language.default()
    response = JsonResponse({
        "default": default.code if default else "",
        "languages": [{"code": language.code, "name": language.name} for language in Language.objects.all()],
    })
    response["Cache-Control"] = "no-store"
    return response
