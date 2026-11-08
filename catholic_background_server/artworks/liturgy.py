# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Liturgical calendar (Roman Rite): seasons and movable celebrations of a date.
Fixed-date celebrations and saints are in the Celebration model (editable).
"""
from datetime import date, timedelta

from django.conf import settings
from django.utils.dates import WEEKDAYS
from django.utils.translation import gettext, gettext_lazy as _

SEASONS = [
    ("advent", _("Advent")),
    ("christmas", _("Christmas")),
    ("lent", _("Lent")),
    ("holy_week", _("Holy Week")),
    ("easter", _("Easter")),
    ("ordinary", _("Ordinary Time")),
]

MOVABLE = [
    ("baptism", _("Baptism of the Lord")),
    ("ash_wednesday", _("Ash Wednesday")),
    ("palm_sunday", _("Palm Sunday")),
    ("holy_thursday", _("Holy Thursday")),
    ("good_friday", _("Good Friday")),
    ("holy_saturday", _("Holy Saturday")),
    ("easter_sunday", _("Easter Sunday")),
    ("divine_mercy", _("Divine Mercy Sunday")),
    ("ascension", _("Ascension of the Lord")),
    ("pentecost", _("Pentecost")),
    ("mary_mother_church", _("Mary, Mother of the Church")),
    ("christ_high_priest", _("Christ the Eternal High Priest")),
    ("trinity", _("Most Holy Trinity")),
    ("corpus_christi", _("Corpus Christi")),
    ("sacred_heart", _("Sacred Heart of Jesus")),
    ("immaculate_heart", _("Immaculate Heart of Mary")),
    ("christ_king", _("Christ the King")),
    ("first_advent", _("First Sunday of Advent")),
    ("holy_family", _("Holy Family")),
]

SUNDAY = 6

# Seasons whose days can be chosen one by one ("Monday of the first week of Advent")
SEASONS_BY_DAY = ("advent", "lent")

# Weeks of those seasons. Lent: 0 = from Ash Wednesday to the Saturday after it, 1-5 = first to
# fifth week, 6 = Holy Week. Advent: 1-4. Each liturgical week begins on Sunday.
SEASON_WEEKS = [
    (0, _("Ash Wednesday to Saturday (Lent)")),
    (1, _("First week")),
    (2, _("Second week")),
    (3, _("Third week")),
    (4, _("Fourth week")),
    (5, _("Fifth week (Lent)")),
    (6, _("Holy Week (Lent)")),
]
WEEKS_OF = {"advent": range(1, 5), "lent": range(0, 7)}

# Days of the week as datetime.weekday() (Monday = 0), in liturgical order: Sunday first
WEEKDAY_CHOICES = [(6, _("Sunday"))] + [(n, WEEKDAYS[n]) for n in range(6)]


def _options():
    return getattr(settings, "CATHOLIC_BACKGROUND", {})


def easter(year):
    """Easter Sunday (Gregorian calendar, anonymous algorithm)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7  # noqa: E741
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)


def next_sunday_after(d):
    return d + timedelta(days=(SUNDAY - d.weekday()) % 7 or 7)


def first_advent(year):
    """First Sunday of Advent: the fourth Sunday before Christmas."""
    christmas = date(year, 12, 25)
    fourth = christmas - timedelta(days=(christmas.weekday() - SUNDAY) % 7 or 7)
    return fourth - timedelta(weeks=3)


def epiphany(year):
    if _options().get("EPIPHANY_ON_SUNDAY"):
        return next_sunday_after(date(year, 1, 1))   # Sunday between 2 and 8 January
    return date(year, 1, 6)


def baptism(year):
    """Baptism of the Lord: Sunday after Epiphany (Monday if Epiphany is on 7 or 8 January)."""
    ep = epiphany(year)
    if ep.weekday() == SUNDAY and ep.day >= 7:
        return ep + timedelta(days=1)
    return next_sunday_after(ep)


def holy_family(year):
    """Sunday within the octave of Christmas, or 30 December if there is none."""
    for day in range(26, 32):
        d = date(year, 12, day)
        if d.weekday() == SUNDAY:
            return d
    return date(year, 12, 30)


def movable_dates(year):
    """{code: date} of the movable celebrations of a year."""
    opts = _options()
    e = easter(year)
    pentecost = e + timedelta(days=49)
    return {
        "baptism": baptism(year),
        "ash_wednesday": e - timedelta(days=46),
        "palm_sunday": e - timedelta(days=7),
        "holy_thursday": e - timedelta(days=3),
        "good_friday": e - timedelta(days=2),
        "holy_saturday": e - timedelta(days=1),
        "easter_sunday": e,
        "divine_mercy": e + timedelta(days=7),
        "ascension": e + timedelta(days=42 if opts.get("ASCENSION_ON_SUNDAY", True) else 39),
        "pentecost": pentecost,
        "mary_mother_church": pentecost + timedelta(days=1),
        "christ_high_priest": pentecost + timedelta(days=4),
        "trinity": pentecost + timedelta(days=7),
        "corpus_christi": pentecost + timedelta(days=14 if opts.get("CORPUS_ON_SUNDAY", True) else 11),
        "sacred_heart": pentecost + timedelta(days=19),
        "immaculate_heart": pentecost + timedelta(days=20),
        "christ_king": first_advent(year) - timedelta(days=7),
        "first_advent": first_advent(year),
        "holy_family": holy_family(year),
    }


def season_day_on(d):
    """
    (season, week, weekday) of a day of Advent or Lent, or None on other days. week as in
    SEASON_WEEKS; weekday as datetime.weekday() (Monday = 0, Sunday = 6).
    """
    advent = first_advent(d.year)
    if advent <= d < date(d.year, 12, 25):
        return "advent", (d - advent).days // 7 + 1, d.weekday()
    e = easter(d.year)
    ash = e - timedelta(days=46)
    if ash <= d < e:
        first_sunday = ash + timedelta(days=4)
        week = 0 if d < first_sunday else (d - first_sunday).days // 7 + 1
        return "lent", week, d.weekday()
    return None


def season_day_text(season, week, weekday):
    text = _season_day_text(season, week, weekday)
    return text[:1].upper() + text[1:]


def _season_day_text(season, week, weekday):
    """
    "Monday of the first week of Advent", in the active language. weekday None: the whole
    week ("First week of Advent").
    """
    season_name = str(dict(SEASONS)[season])
    day = str(dict(WEEKDAY_CHOICES)[weekday]) if weekday is not None else ""
    movable = dict(MOVABLE)
    # Days with a name of their own
    own = {("lent", 0, 2): "ash_wednesday", ("lent", 6, SUNDAY): "palm_sunday", ("lent", 6, 3): "holy_thursday",
           ("lent", 6, 4): "good_friday", ("lent", 6, 5): "holy_saturday"}
    if (season, week, weekday) in own:
        return str(movable[own[season, week, weekday]])
    if weekday == SUNDAY:
        sundays = [gettext("First Sunday of %(season)s"), gettext("Second Sunday of %(season)s"),
                   gettext("Third Sunday of %(season)s"), gettext("Fourth Sunday of %(season)s"),
                   gettext("Fifth Sunday of %(season)s")]
        return sundays[week - 1] % {"season": season_name}
    if season == "lent" and week == 0:
        return gettext("%(weekday)s after Ash Wednesday") % {"weekday": day} if day else gettext("Days after Ash Wednesday")
    if season == "lent" and week == 6:
        return gettext("%(weekday)s of Holy Week") % {"weekday": day} if day else str(dict(SEASONS)["holy_week"])
    ordinal = [gettext("first"), gettext("second"), gettext("third"), gettext("fourth"), gettext("fifth")][week - 1]
    if day:
        return gettext("%(weekday)s of the %(ordinal)s week of %(season)s") % {
            "weekday": day, "ordinal": ordinal, "season": season_name}
    return gettext("The %(ordinal)s week of %(season)s") % {"ordinal": ordinal, "season": season_name}


def movable_codes_on(d):
    return {code for code, when in movable_dates(d.year).items() if when == d}


def seasons_on(d):
    """Liturgical seasons of a date (Holy Week is also Lent)."""
    e = easter(d.year)
    if first_advent(d.year) <= d < date(d.year, 12, 25):
        return {"advent"}
    if d >= date(d.year, 12, 25) or d <= baptism(d.year):
        return {"christmas"}
    if e - timedelta(days=46) <= d < e:
        return {"lent", "holy_week"} if d >= e - timedelta(days=7) else {"lent"}
    if e <= d <= e + timedelta(days=49):
        return {"easter"}
    return {"ordinary"}
