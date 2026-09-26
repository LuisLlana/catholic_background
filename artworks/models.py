# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from . import liturgy
from .validators import validate_image

KIND_CHOICES = [
    ("lord", "Of the Lord"),
    ("mary", "Of the Virgin Mary"),
    ("saint", "Saint"),
    ("other", "Other"),
]
RANK_CHOICES = [
    ("solemnity", "Solemnity"),
    ("feast", "Feast"),
    ("memorial", "Memorial"),
    ("optional", "Optional memorial"),
    ("other", "Other"),
]
MONTH_CHOICES = [(i, name) for i, name in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], start=1)]


class Celebration(models.Model):
    """A celebration of the liturgical calendar: fixed date or movable (computed every year)."""

    name = models.CharField("name", max_length=200)
    kind = models.CharField("kind", max_length=10, choices=KIND_CHOICES, default="saint")
    rank = models.CharField("rank", max_length=10, choices=RANK_CHOICES, default="memorial")
    month = models.PositiveSmallIntegerField("month", choices=MONTH_CHOICES, null=True, blank=True)
    day = models.PositiveSmallIntegerField("day", null=True, blank=True)
    movable = models.CharField("movable celebration", max_length=30, choices=liturgy.MOVABLE, blank=True,
                               help_text="For celebrations whose date changes every year (computed from Easter).")
    notes = models.TextField("notes", blank=True)

    class Meta:
        verbose_name = "celebration"
        verbose_name_plural = "calendar of celebrations"
        ordering = ["month", "day", "name"]

    def __str__(self):
        return self.name

    def clean(self):
        fixed = self.month is not None or self.day is not None
        if bool(self.movable) == fixed:
            raise ValidationError("Give either a fixed date (month and day) or a movable celebration, not both.")
        if fixed:
            if self.month is None or self.day is None:
                raise ValidationError("Give the month and the day.")
            try:
                date(2024, self.month, self.day)   # leap year: allows 29 February
            except ValueError:
                raise ValidationError("That date does not exist.")

    def when(self):
        if self.movable:
            return dict(liturgy.MOVABLE).get(self.movable, self.movable) + " (movable)"
        if self.month and self.day:
            return f"{dict(MONTH_CHOICES)[self.month]} {self.day}"
        return ""
    when.short_description = "date"


class MetadataKey(models.Model):
    """Names of the extra data of the artworks (museum, technique...), shared by all editors."""

    name = models.CharField("name", max_length=100, unique=True)
    order = models.PositiveSmallIntegerField("order", default=0)

    class Meta:
        verbose_name = "kind of additional data"
        verbose_name_plural = "kinds of additional data"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class Artwork(models.Model):
    image = models.ImageField("image", upload_to="artworks/%Y/", validators=[validate_image],
                              help_text="JPEG or PNG. Only the artwork, without added frames or backgrounds.")
    title = models.CharField("title", max_length=300, blank=True)
    author = models.CharField("author", max_length=300, blank=True)
    year = models.CharField("year", max_length=100, blank=True, help_text="Free text: “1426”, “c. 1450”, “1450–1455”…")
    description = models.TextField("comment", blank=True, help_text="What the artwork shows and any useful explanation.")
    source_url = models.URLField("source", max_length=500, blank=True,
                                 help_text="Address of the page the image was taken from.")
    license = models.CharField("license", max_length=200, blank=True,
                               help_text="For example: “Public domain”, “CC0”, “CC BY 4.0”.")

    approved = models.BooleanField("approved", default=False)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="approved by", null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="+")
    approved_at = models.DateTimeField("approved at", null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="uploaded by", null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField("created at", auto_now_add=True)
    updated_at = models.DateTimeField("updated at", auto_now=True)

    class Meta:
        verbose_name = "artwork"
        verbose_name_plural = "artworks"
        ordering = ["-created_at"]
        permissions = [("approve_artwork", "Can approve artworks")]

    def __str__(self):
        return self.title or self.author or f"Artwork {self.pk}"

    def extra(self):
        return {m.key.name: m.value for m in self.metadata.select_related("key").all() if m.value}


class ArtworkMetadata(models.Model):
    artwork = models.ForeignKey(Artwork, on_delete=models.CASCADE, related_name="metadata")
    key = models.ForeignKey(MetadataKey, verbose_name="data", on_delete=models.PROTECT)
    value = models.CharField("value", max_length=500)

    class Meta:
        verbose_name = "additional data"
        verbose_name_plural = "other data"
        constraints = [models.UniqueConstraint(fields=["artwork", "key"], name="unique_metadata_per_artwork")]

    def __str__(self):
        return f"{self.key}: {self.value}"


CONDITION_TYPES = [
    ("season", "Liturgical season"),
    ("celebration", "Celebration (of the Lord, of the Virgin…)"),
    ("saint", "Saint of the day"),
    ("yearly_date", "Date of every year"),
    ("date", "Specific date"),
    ("any", "Any day (reserve)"),
]


class Condition(models.Model):
    """When an artwork can be shown. An artwork is shown on days that meet ANY of its conditions."""

    artwork = models.ForeignKey(Artwork, on_delete=models.CASCADE, related_name="conditions")
    type = models.CharField("when", max_length=20, choices=CONDITION_TYPES)
    season = models.CharField("liturgical season", max_length=20, choices=liturgy.SEASONS, blank=True)
    celebration = models.ForeignKey(Celebration, verbose_name="celebration or saint", null=True, blank=True,
                                    on_delete=models.PROTECT)
    month = models.PositiveSmallIntegerField("month", choices=MONTH_CHOICES, null=True, blank=True)
    day = models.PositiveSmallIntegerField("day", null=True, blank=True)
    date = models.DateField("date", null=True, blank=True)

    class Meta:
        verbose_name = "when it is shown"
        verbose_name_plural = "when it is shown (it is enough to meet one)"

    def __str__(self):
        if self.type == "season":
            return dict(liturgy.SEASONS).get(self.season, "")
        if self.type in ("celebration", "saint"):
            return str(self.celebration or "")
        if self.type == "yearly_date" and self.month and self.day:
            return f"Every {dict(MONTH_CHOICES)[self.month]} {self.day}"
        if self.type == "date" and self.date:
            return self.date.strftime("%d/%m/%Y")
        return dict(CONDITION_TYPES).get(self.type, "")

    def clean(self):
        required = {
            "season": ["season"], "celebration": ["celebration"], "saint": ["celebration"],
            "yearly_date": ["month", "day"], "date": ["date"], "any": [],
        }.get(self.type, [])
        errors = {field: "Required for this kind." for field in required if getattr(self, field) in (None, "")}
        if errors:
            raise ValidationError(errors)
        if self.type == "yearly_date":
            try:
                date(2024, self.month, self.day)
            except ValueError:
                raise ValidationError({"day": "That date does not exist."})
        # Keep only the fields of the chosen type
        for field in ("season", "celebration", "month", "day", "date"):
            if field not in required:
                setattr(self, field, "" if field == "season" else None)


class AccessLog(models.Model):
    """Requests of the applications (IP addresses are personal data: deleted after ACCESS_LOG_DAYS)."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    # Local day, stored explicitly: grouping by day then works the same in every database
    day = models.DateField(db_index=True)
    ip = models.GenericIPAddressField(null=True)
    user_agent = models.CharField(max_length=300, blank=True)
    artwork = models.ForeignKey(Artwork, null=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        verbose_name = "access"
        verbose_name_plural = "accesses"


class DailyStatistic(models.Model):
    """Aggregated usage per day, without IP addresses (kept indefinitely)."""

    day = models.DateField("day", unique=True)
    requests = models.PositiveIntegerField("requests", default=0)
    clients = models.PositiveIntegerField("different computers", default=0)

    class Meta:
        verbose_name = "daily statistic"
        verbose_name_plural = "daily statistics"
        ordering = ["-day"]

    def __str__(self):
        return str(self.day)
