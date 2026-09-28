# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _

from . import liturgy
from .validators import validate_image

KIND_CHOICES = [
    ("lord", _("Of the Lord")),
    ("mary", _("Of the Virgin Mary")),
    ("saint", _("Saint")),
    ("other", _("Other")),
]
RANK_CHOICES = [
    ("solemnity", _("Solemnity")),
    ("feast", _("Feast")),
    ("memorial", _("Memorial")),
    ("optional", _("Optional memorial")),
    ("other", _("Other")),
]
MONTH_CHOICES = [(i, name) for i, name in enumerate(
    [_("January"), _("February"), _("March"), _("April"), _("May"), _("June"), _("July"),
     _("August"), _("September"), _("October"), _("November"), _("December")], start=1)]


class Language(models.Model):
    """Languages of the content (texts of the artworks). The administrator can add more."""

    code = models.CharField(
        _("code"), max_length=10, unique=True,
        validators=[RegexValidator(r"^[a-z]{2,3}(-[a-z0-9]{2,8})?$", _("Use a code such as “es”, “en” or “pt-br”."))],
        help_text=_("Language code: “es”, “en”, “fr”, “pt-br”…"))
    name = models.CharField(_("name"), max_length=100, help_text=_("Name of the language in that language: “Español”, “English”…"))
    order = models.PositiveSmallIntegerField(_("order"), default=0)
    is_default = models.BooleanField(
        _("default"), default=False,
        help_text=_("Used when the application does not ask for a language or asks for one that is not available."))

    class Meta:
        verbose_name = _("language")
        verbose_name_plural = _("languages")
        ordering = ["order", "code"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_default:
            Language.objects.exclude(pk=self.pk).filter(is_default=True).update(is_default=False)

    @classmethod
    def default(cls):
        return cls.objects.filter(is_default=True).first() or cls.objects.first()

    @classmethod
    def best_match(cls, codes):
        """First available language of a list of codes (e.g. from Accept-Language); None if none."""
        languages = list(cls.objects.all())
        for code in codes:
            code = (code or "").lower().replace("_", "-")
            if not code:
                continue
            for language in languages:
                if language.code == code:
                    return language
            for language in languages:
                if language.code.split("-")[0] == code.split("-")[0]:
                    return language
        return None


def current_language():
    """Content language matching the language of the interface, or the default one."""
    return Language.best_match([get_language()]) or Language.default()


class Celebration(models.Model):
    """A celebration of the liturgical calendar: fixed date or movable (computed every year)."""

    name = models.CharField(_("name"), max_length=200)
    name_es = models.CharField(_("name in Spanish"), max_length=200, blank=True,
                               help_text=_("Shown when the site is in Spanish (if empty, the name is used)."))
    kind = models.CharField(_("kind"), max_length=10, choices=KIND_CHOICES, default="saint")
    rank = models.CharField(_("rank"), max_length=10, choices=RANK_CHOICES, default="memorial")
    month = models.PositiveSmallIntegerField(_("month"), choices=MONTH_CHOICES, null=True, blank=True)
    day = models.PositiveSmallIntegerField(_("day"), null=True, blank=True)
    movable = models.CharField(_("movable celebration"), max_length=30, choices=liturgy.MOVABLE, blank=True,
                               help_text=_("For celebrations whose date changes every year (computed from Easter)."))
    notes = models.TextField(_("notes"), blank=True)

    class Meta:
        verbose_name = _("celebration")
        verbose_name_plural = _("calendar of celebrations")
        ordering = ["month", "day", "name"]

    def __str__(self):
        return self.localized_name

    @property
    def localized_name(self):
        if self.name_es and (get_language() or "").startswith("es"):
            return self.name_es
        return self.name

    def clean(self):
        fixed = self.month is not None or self.day is not None
        if bool(self.movable) == fixed:
            raise ValidationError(_("Give either a fixed date (month and day) or a movable celebration, not both."))
        if fixed:
            if self.month is None or self.day is None:
                raise ValidationError(_("Give the month and the day."))
            try:
                date(2024, self.month, self.day)   # leap year: allows 29 February
            except ValueError:
                raise ValidationError(_("That date does not exist."))

    def when(self):
        if self.movable:
            return _("%(name)s (movable)") % {"name": dict(liturgy.MOVABLE).get(self.movable, self.movable)}
        if self.month and self.day:
            return _("%(month)s %(day)s") % {"month": dict(MONTH_CHOICES)[self.month], "day": self.day}
        return ""
    when.short_description = _("date")


class MetadataKey(models.Model):
    """Names of the extra data of the artworks (museum, technique...), shared by all editors."""

    name = models.CharField(_("name"), max_length=100, unique=True)
    order = models.PositiveSmallIntegerField(_("order"), default=0)

    class Meta:
        verbose_name = _("kind of additional data")
        verbose_name_plural = _("kinds of additional data")
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    def name_in(self, language):
        """Name in a language (the internal name if it has no translation)."""
        for translated in self.names.all():
            if language and translated.language_id == language.pk and translated.name:
                return translated.name
        return self.name


class MetadataKeyName(models.Model):
    key = models.ForeignKey(MetadataKey, on_delete=models.CASCADE, related_name="names")
    language = models.ForeignKey(Language, verbose_name=_("language"), on_delete=models.PROTECT)
    name = models.CharField(_("name"), max_length=100)

    class Meta:
        verbose_name = _("name in a language")
        verbose_name_plural = _("names in each language")
        constraints = [models.UniqueConstraint(fields=["key", "language"], name="unique_key_name_per_language")]

    def __str__(self):
        return self.name


TEXT_FIELDS = ("title", "author", "year", "description", "license")


def _by_preference(items, language):
    """Items with a .language: the requested one first, then the default one, then by order."""
    wanted = getattr(language, "pk", None)
    return sorted(items, key=lambda i: (i.language_id != wanted, not i.language.is_default, i.language.order, i.language.code))


class Artwork(models.Model):
    image = models.ImageField(_("image"), upload_to="artworks/%Y/", validators=[validate_image],
                              help_text=_("JPEG or PNG. Only the artwork, without added frames or backgrounds."))
    source_url = models.URLField(_("source"), max_length=500, blank=True,
                                 help_text=_("Address of the page the image was taken from."))
    approved = models.BooleanField(_("approved"), default=False)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_("approved by"), null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="+")
    approved_at = models.DateTimeField(_("approved at"), null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_("uploaded by"), null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("artwork")
        verbose_name_plural = _("artworks")
        ordering = ["-created_at"]
        permissions = [("approve_artwork", "Can approve artworks")]

    def __str__(self):
        texts = self.texts(current_language()) if self.pk else {}
        return texts.get("title") or texts.get("author") or _("Artwork %(id)s") % {"id": self.pk}

    def texts(self, language=None):
        """
        Title, author, year, description and license in a language. Every empty field is taken
        from the default language or, if empty too, from any other; "language" is the language
        of the main text.
        """
        ordered = _by_preference(list(self.translations.select_related("language")), language)
        result = {field: next((getattr(t, field) for t in ordered if getattr(t, field)), "") for field in TEXT_FIELDS}
        result["language"] = ordered[0].language.code if ordered else getattr(language, "code", "")
        return result

    def extra(self, language=None):
        """Additional data in a language (each value falls back like the texts)."""
        rows = _by_preference(list(self.metadata.select_related("key", "language").prefetch_related("key__names")), language)
        result = {}
        for row in rows:
            name = row.key.name_in(language)
            if row.value and name not in result:
                result[name] = row.value
        return result


class ArtworkTranslation(models.Model):
    """Texts of an artwork in one language."""

    artwork = models.ForeignKey(Artwork, on_delete=models.CASCADE, related_name="translations")
    language = models.ForeignKey(Language, verbose_name=_("language"), on_delete=models.PROTECT)
    title = models.CharField(_("title"), max_length=300, blank=True)
    author = models.CharField(_("author"), max_length=300, blank=True)
    year = models.CharField(_("year"), max_length=100, blank=True, help_text=_("Free text: “1426”, “c. 1450”, “1450–1455”…"))
    description = models.TextField(_("comment"), blank=True, help_text=_("What the artwork shows and any useful explanation."))
    license = models.CharField(_("license"), max_length=200, blank=True,
                               help_text=_("For example: “Public domain”, “CC0”, “CC BY 4.0”."))

    class Meta:
        verbose_name = _("texts in a language")
        verbose_name_plural = _("texts (one block per language)")
        ordering = ["language__order", "language__code"]
        constraints = [models.UniqueConstraint(fields=["artwork", "language"], name="unique_translation_per_language")]

    def __str__(self):
        return f"{self.language}: {self.title}"


class ArtworkMetadata(models.Model):
    artwork = models.ForeignKey(Artwork, on_delete=models.CASCADE, related_name="metadata")
    key = models.ForeignKey(MetadataKey, verbose_name=_("data"), on_delete=models.PROTECT)
    language = models.ForeignKey(Language, verbose_name=_("language"), on_delete=models.PROTECT)
    value = models.CharField(_("value"), max_length=500)

    class Meta:
        verbose_name = _("additional data")
        verbose_name_plural = _("other data")
        constraints = [models.UniqueConstraint(fields=["artwork", "key", "language"], name="unique_metadata_per_language")]

    def __str__(self):
        return f"{self.key} ({self.language}): {self.value}"


CONDITION_TYPES = [
    ("season", _("Liturgical season")),
    ("celebration", _("Celebration (of the Lord, of the Virgin…)")),
    ("saint", _("Saint of the day")),
    ("yearly_date", _("Date of every year")),
    ("date", _("Specific date")),
    ("any", _("Any day (reserve)")),
]


class Condition(models.Model):
    """When an artwork can be shown. An artwork is shown on days that meet ANY of its conditions."""

    artwork = models.ForeignKey(Artwork, on_delete=models.CASCADE, related_name="conditions")
    type = models.CharField(_("when"), max_length=20, choices=CONDITION_TYPES)
    season = models.CharField(_("liturgical season"), max_length=20, choices=liturgy.SEASONS, blank=True)
    celebration = models.ForeignKey(Celebration, verbose_name=_("celebration or saint"), null=True, blank=True,
                                    on_delete=models.PROTECT)
    month = models.PositiveSmallIntegerField(_("month"), choices=MONTH_CHOICES, null=True, blank=True)
    day = models.PositiveSmallIntegerField(_("day"), null=True, blank=True)
    date = models.DateField(_("date"), null=True, blank=True)

    class Meta:
        verbose_name = _("when it is shown")
        verbose_name_plural = _("when it is shown (it is enough to meet one)")

    def __str__(self):
        if self.type == "season":
            return str(dict(liturgy.SEASONS).get(self.season, ""))
        if self.type in ("celebration", "saint"):
            return str(self.celebration or "")
        if self.type == "yearly_date" and self.month and self.day:
            return _("Every %(month)s %(day)s") % {"month": dict(MONTH_CHOICES)[self.month], "day": self.day}
        if self.type == "date" and self.date:
            return self.date.strftime("%d/%m/%Y")
        return str(dict(CONDITION_TYPES).get(self.type, ""))

    def clean(self):
        required = {
            "season": ["season"], "celebration": ["celebration"], "saint": ["celebration"],
            "yearly_date": ["month", "day"], "date": ["date"], "any": [],
        }.get(self.type, [])
        errors = {field: _("Required for this kind.") for field in required if getattr(self, field) in (None, "")}
        if errors:
            raise ValidationError(errors)
        if self.type == "yearly_date":
            try:
                date(2024, self.month, self.day)
            except ValueError:
                raise ValidationError({"day": _("That date does not exist.")})
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
        verbose_name = _("access")
        verbose_name_plural = _("accesses")


class DailyStatistic(models.Model):
    """Aggregated usage per day, without IP addresses (kept indefinitely)."""

    day = models.DateField(_("day"), unique=True)
    requests = models.PositiveIntegerField(_("requests"), default=0)
    clients = models.PositiveIntegerField(_("different computers"), default=0)

    class Meta:
        verbose_name = _("daily statistic")
        verbose_name_plural = _("daily statistics")
        ordering = ["-day"]

    def __str__(self):
        return str(self.day)
