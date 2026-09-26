# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Which artwork is shown for a given day and moment."""
from django.db.models import Q

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
