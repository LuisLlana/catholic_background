# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Which artwork is shown for a given day and moment."""
from django.db.models import Q
from django.utils import translation

from . import liturgy
from .models import Artwork, Celebration


def celebrations_on(day):
    movable = liturgy.movable_codes_on(day)
    return Celebration.objects.filter(Q(month=day.month, day=day.day) | Q(movable__in=movable))


def candidates(day):
    """
    Approved artworks for a day: those with ANY condition met by the day.
    If there are none, the ones marked "any day" (reserve).
    """
    matches = (
        Q(conditions__type="season", conditions__season__in=liturgy.seasons_on(day))
        | Q(conditions__type__in=["celebration", "saint"], conditions__celebration__in=celebrations_on(day))
        | Q(conditions__type="yearly_date", conditions__month=day.month, conditions__day=day.day)
        | Q(conditions__type="date", conditions__date=day)
    )
    approved = Artwork.objects.filter(approved=True)
    found = list(approved.filter(matches).distinct().order_by("id"))
    if not found:
        found = list(approved.filter(conditions__type="any").distinct().order_by("id"))
    return found


def pick(day, seconds_into_day):
    """With several candidates, each one is shown in turn during an equal part of the day."""
    found = candidates(day)
    if not found:
        return None
    slot = int(max(0, min(86399, seconds_into_day)) * len(found) // 86400)
    return found[slot]


# Most specific first: a saint or a celebration explains the choice better than a season
REASON_ORDER = ("saint", "celebration", "season")


def reason(artwork, day, language=None):
    """
    Why the artwork is shown on that day, in the language of the content:
    {"text": "Saint Joseph…", "type": "saint"}. Empty for dates and "any day".
    """
    seasons = liturgy.seasons_on(day)
    celebrations = {c.pk: c for c in celebrations_on(day)}
    met = []
    for condition in artwork.conditions.all():
        if condition.type in ("saint", "celebration") and condition.celebration_id in celebrations:
            met.append((condition.type, celebrations[condition.celebration_id]))
        elif condition.type == "season" and condition.season in seasons:
            met.append(("season", condition.season))
    if not met:
        return {"text": "", "type": ""}
    kind, value = min(met, key=lambda item: REASON_ORDER.index(item[0]))
    code = getattr(language, "code", "") or ""
    if kind == "season":
        # Names of the seasons are interface texts: translated when there is a catalogue for the language
        with translation.override(code or None):
            text = str(dict(liturgy.SEASONS)[value])
    else:
        text = value.name_es if code.startswith("es") and value.name_es else value.name
    return {"text": text, "type": kind}
