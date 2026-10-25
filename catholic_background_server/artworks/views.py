# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
import base64
import time
from datetime import date, datetime, timedelta, timezone

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import render
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.html import format_html
from django.utils import timezone as dj_timezone
from django.utils.translation import get_language
from django.views.decorators.http import require_GET

from .caption import labelled_jpeg
from .models import AccessLog, Artwork, Language, current_language
from .selection import candidates, pick, pick_next, reason



def requested_language(request):
    """
    ?lang=xx, else the default language of the content. The Accept-Language header is not
    used on purpose: the image (with its label) must be the same for the same request,
    whatever HTTP library the application uses.
    """
    return Language.best_match([request.GET.get("lang", "")]) or Language.default()


NULL_VALUES = ("", "0", "false", "no", "off")


def wants_caption(request):
    value = request.GET.get("caption")
    if value is None:
        return settings.CATHOLIC_BACKGROUND["CAPTION_DEFAULT"]
    return value.lower() not in NULL_VALUES


def wants_raw(request):
    """raw=<non null value>: the image itself instead of the JSON document."""
    return request.GET.get("raw", "").lower() not in NULL_VALUES


def image_type(data):
    """Only JPEG and PNG images are accepted (see validators)."""
    return ("image/png", "png") if data.startswith(b"\x89PNG\r\n\x1a\n") else ("image/jpeg", "jpg")


def requested_next(request):
    """
    next: another artwork of the day, the one after the artwork whose id is given (next=<id>),
    or after the current turn (next with no value). None if the parameter is not there.
    Returns (True, id or None) when it is there.
    """
    if "next" not in request.GET:
        return False, None
    value = request.GET["next"].strip()
    return True, int(value) if value.isdigit() else None


def client_ip(request):
    if getattr(settings, "TRUST_X_FORWARDED_FOR", False):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


@require_GET
def background(request):
    """
    GET /background?ts=<Unix timestamp of the client's local midnight>[&lang=<language code>][&caption=0][&raw=1]
                   [&next[=<id>]]
    -> {"image": base64, "title", "author", "date", "description", "source", "license", "extra", "language",
        "reason", "reason_type", "id", "edit_url", "position", "count"}
    "reason" says why the artwork is shown that day (saint, celebration or liturgical season), if it is special.
    "id" and "edit_url" identify the artwork and give the page of the admin site to edit it.
    Any day can be asked for with ts, past or future.
    raw=<non null value> sends the image itself (image/jpeg or image/png) instead of the JSON document.
    next=<id> sends the artwork of the day that follows the one with that id (in a fixed order,
    back to the first after the last); next with no value, the one after the current turn.
    "position" (from 1) and "count" place the artwork among those of the day.
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
    seconds = (now - ts) % 86400
    wants_next, after = requested_next(request)
    if wants_next:
        chosen = pick_next(day, seconds, after)
        if chosen is None:
            return JsonResponse({"error": "no image for this day"}, status=404)
        artwork, position, count = chosen
    else:
        artwork = pick(day, seconds)
        if artwork is None:
            return JsonResponse({"error": "no image for this day"}, status=404)
        ids = [found.pk for found in candidates(day)]
        position, count = ids.index(artwork.pk) + 1, len(ids)

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

    AccessLog.objects.create(day=dj_timezone.localdate(), ip=client_ip(request),
                             user_agent=request.META.get("HTTP_USER_AGENT", "")[:300],
                             artwork=artwork)

    if wants_raw(request):
        content_type, extension = image_type(data)
        response = HttpResponse(data, content_type=content_type)
        response["Content-Disposition"] = f'inline; filename="artwork-{artwork.pk}.{extension}"'
        response["Cache-Control"] = "no-store"
        response["Content-Language"] = texts["language"]
        return response

    image = base64.b64encode(data).decode("ascii")

    response = JsonResponse({
        "image": image,
        "title": texts["title"],
        "author": texts["author"],
        "date": texts["year"],
        "description": texts["description"],
        "source": artwork.source_url,
        "license": texts["license"],
        "extra": artwork.additional_data(language),
        "language": texts["language"],
        "reason": why["text"],
        "reason_type": why["type"],
        "id": artwork.pk,
        # Place among the artworks of the day (next=<id> goes to the following one)
        "position": position,
        "count": count,
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


def source_link(url):
    """Link to the source of an artwork: only http(s) addresses become links (never javascript: and the like)."""
    if url.lower().startswith(("http://", "https://")):
        return format_html('<a href="{}" rel="noopener noreferrer">{}</a>', url, url)
    return url


def _browser_day(value):
    """Day asked for in the browser (?date=YYYY-MM-DD); today if missing or not valid."""
    try:
        return datetime.strptime(value or "", "%Y-%m-%d").date()
    except ValueError:
        return dj_timezone.localdate()


@require_GET
def browser(request):
    """
    Web page with the image of any day and its data, like the desktop applications.
    ?date=YYYY-MM-DD (default: today) and ?lang=<language of the texts> (default: that of the page).
    ?next=<id>: the artwork of the day that follows that one ("Next image", when the day has several).
    """
    day = _browser_day(request.GET.get("date"))
    language = Language.best_match([request.GET.get("lang", "")]) or current_language()
    now = dj_timezone.localtime()
    seconds = (now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()
    wants_next, after = requested_next(request)
    position = count = 0
    if wants_next:
        chosen = pick_next(day, seconds, after)
        artwork = chosen[0] if chosen else None
        if chosen:
            position, count = chosen[1], chosen[2]
    else:
        artwork = pick(day, seconds)
        if artwork is not None:
            ids = [found.pk for found in candidates(day)]
            position, count = ids.index(artwork.pk) + 1, len(ids)

    context = {
        "day": day,
        "today": dj_timezone.localdate(),
        "previous": day - timedelta(days=1) if day > date.min else None,
        "next": day + timedelta(days=1) if day < date.max else None,
        "language": language,
        "languages": Language.objects.all(),
        "artwork": artwork,
        # Place among the artworks of the day, for "Next image"
        "position": position,
        "count": count,
    }
    if artwork is not None:
        context.update({
            "texts": artwork.texts(language),
            "reason": reason(artwork, day, language)["text"],
            "additional": artwork.additional_data(language),
            "source": source_link(artwork.source_url),
            "can_edit": request.user.is_active and request.user.is_staff,
        })
    return render(request, "pages/browser.html", context)


@require_GET
def browser_image(request, pk):
    """The image of an approved artwork, for the browser page (without label)."""
    artwork = get_object_or_404(Artwork, pk=pk, approved=True)
    try:
        with artwork.image.open("rb") as f:
            data = f.read()
    except (FileNotFoundError, ValueError, OSError):
        raise Http404
    content_type, _ = image_type(data)
    response = HttpResponse(data, content_type=content_type)
    response["Cache-Control"] = "public, max-age=3600"
    return response
