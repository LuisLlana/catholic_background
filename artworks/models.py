# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from . import liturgy
from .validators import validate_image

KIND_CHOICES = [
    ("lord", "Del Señor"),
    ("mary", "De la Virgen María"),
    ("saint", "Santo o santa"),
    ("other", "Otra"),
]
RANK_CHOICES = [
    ("solemnity", "Solemnidad"),
    ("feast", "Fiesta"),
    ("memorial", "Memoria obligatoria"),
    ("optional", "Memoria libre"),
    ("other", "Otra"),
]
MONTH_CHOICES = [(i, name) for i, name in enumerate(
    ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
     "agosto", "septiembre", "octubre", "noviembre", "diciembre"], start=1)]


class Celebration(models.Model):
    """A celebration of the liturgical calendar: fixed date or movable (computed every year)."""

    name = models.CharField("nombre", max_length=200)
    kind = models.CharField("tipo", max_length=10, choices=KIND_CHOICES, default="saint")
    rank = models.CharField("grado", max_length=10, choices=RANK_CHOICES, default="memorial")
    month = models.PositiveSmallIntegerField("mes", choices=MONTH_CHOICES, null=True, blank=True)
    day = models.PositiveSmallIntegerField("día", null=True, blank=True)
    movable = models.CharField("fiesta móvil", max_length=30, choices=liturgy.MOVABLE, blank=True,
                               help_text="Para fiestas que cambian de fecha cada año (se calculan a partir de la Pascua).")
    notes = models.TextField("notas", blank=True)

    class Meta:
        verbose_name = "celebración"
        verbose_name_plural = "calendario de celebraciones"
        ordering = ["month", "day", "name"]

    def __str__(self):
        return self.name

    def clean(self):
        fixed = self.month is not None or self.day is not None
        if bool(self.movable) == fixed:
            raise ValidationError("Indica una fecha fija (mes y día) o una fiesta móvil, pero no las dos.")
        if fixed:
            if self.month is None or self.day is None:
                raise ValidationError("Indica el mes y el día.")
            try:
                date(2024, self.month, self.day)   # leap year: allows 29 February
            except ValueError:
                raise ValidationError("Esa fecha no existe.")

    def when(self):
        if self.movable:
            return dict(liturgy.MOVABLE).get(self.movable, self.movable) + " (móvil)"
        if self.month and self.day:
            return f"{self.day} de {dict(MONTH_CHOICES)[self.month]}"
        return ""
    when.short_description = "fecha"


class MetadataKey(models.Model):
    """Names of the extra data of the artworks (museum, technique...), shared by all editors."""

    name = models.CharField("nombre", max_length=100, unique=True)
    order = models.PositiveSmallIntegerField("orden", default=0)

    class Meta:
        verbose_name = "tipo de dato adicional"
        verbose_name_plural = "tipos de datos adicionales"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class Artwork(models.Model):
    image = models.ImageField("imagen", upload_to="artworks/%Y/", validators=[validate_image],
                              help_text="JPEG o PNG. Solo la obra, sin marcos ni fondos añadidos.")
    title = models.CharField("título", max_length=300, blank=True)
    author = models.CharField("autor", max_length=300, blank=True)
    year = models.CharField("año", max_length=100, blank=True, help_text="Texto libre: «1426», «c. 1450», «1450–1455»…")
    description = models.TextField("comentario", blank=True, help_text="Qué aparece en la obra y cualquier explicación útil.")
    source_url = models.URLField("procedencia", max_length=500, blank=True,
                                 help_text="Dirección de la página de donde se ha obtenido la imagen.")
    license = models.CharField("licencia", max_length=200, blank=True,
                               help_text="Por ejemplo: «Dominio público», «CC0», «CC BY 4.0».")

    approved = models.BooleanField("aprobada", default=False)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="aprobada por", null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="+")
    approved_at = models.DateTimeField("aprobada el", null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="subida por", null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField("creada el", auto_now_add=True)
    updated_at = models.DateTimeField("modificada el", auto_now=True)

    class Meta:
        verbose_name = "obra"
        verbose_name_plural = "obras"
        ordering = ["-created_at"]
        permissions = [("approve_artwork", "Puede aprobar obras")]

    def __str__(self):
        return self.title or self.author or f"Obra {self.pk}"

    def extra(self):
        return {m.key.name: m.value for m in self.metadata.select_related("key").all() if m.value}


class ArtworkMetadata(models.Model):
    artwork = models.ForeignKey(Artwork, on_delete=models.CASCADE, related_name="metadata")
    key = models.ForeignKey(MetadataKey, verbose_name="dato", on_delete=models.PROTECT)
    value = models.CharField("valor", max_length=500)

    class Meta:
        verbose_name = "dato adicional"
        verbose_name_plural = "otros datos"
        constraints = [models.UniqueConstraint(fields=["artwork", "key"], name="unique_metadata_per_artwork")]

    def __str__(self):
        return f"{self.key}: {self.value}"


CONDITION_TYPES = [
    ("season", "Tiempo litúrgico"),
    ("celebration", "Celebración (del Señor, de la Virgen…)"),
    ("saint", "Santo del día"),
    ("yearly_date", "Fecha de todos los años"),
    ("date", "Fecha concreta"),
    ("any", "Cualquier día (de reserva)"),
]


class Condition(models.Model):
    """When an artwork can be shown. An artwork is shown on days that meet ANY of its conditions."""

    artwork = models.ForeignKey(Artwork, on_delete=models.CASCADE, related_name="conditions")
    type = models.CharField("cuándo", max_length=20, choices=CONDITION_TYPES)
    season = models.CharField("tiempo litúrgico", max_length=20, choices=liturgy.SEASONS, blank=True)
    celebration = models.ForeignKey(Celebration, verbose_name="celebración o santo", null=True, blank=True,
                                    on_delete=models.PROTECT)
    month = models.PositiveSmallIntegerField("mes", choices=MONTH_CHOICES, null=True, blank=True)
    day = models.PositiveSmallIntegerField("día", null=True, blank=True)
    date = models.DateField("fecha", null=True, blank=True)

    class Meta:
        verbose_name = "cuándo se muestra"
        verbose_name_plural = "cuándo se muestra (basta con que se cumpla una)"

    def __str__(self):
        if self.type == "season":
            return dict(liturgy.SEASONS).get(self.season, "")
        if self.type in ("celebration", "saint"):
            return str(self.celebration or "")
        if self.type == "yearly_date" and self.month and self.day:
            return f"Cada {self.day} de {dict(MONTH_CHOICES)[self.month]}"
        if self.type == "date" and self.date:
            return self.date.strftime("%d/%m/%Y")
        return dict(CONDITION_TYPES).get(self.type, "")

    def clean(self):
        required = {
            "season": ["season"], "celebration": ["celebration"], "saint": ["celebration"],
            "yearly_date": ["month", "day"], "date": ["date"], "any": [],
        }.get(self.type, [])
        errors = {field: "Obligatorio para este tipo." for field in required if getattr(self, field) in (None, "")}
        if errors:
            raise ValidationError(errors)
        if self.type == "yearly_date":
            try:
                date(2024, self.month, self.day)
            except ValueError:
                raise ValidationError({"day": "Esa fecha no existe."})
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
        verbose_name = "acceso"
        verbose_name_plural = "accesos"


class DailyStatistic(models.Model):
    """Aggregated usage per day, without IP addresses (kept indefinitely)."""

    day = models.DateField("día", unique=True)
    requests = models.PositiveIntegerField("peticiones", default=0)
    clients = models.PositiveIntegerField("equipos distintos", default=0)

    class Meta:
        verbose_name = "estadística diaria"
        verbose_name_plural = "estadísticas diarias"
        ordering = ["-day"]

    def __str__(self):
        return str(self.day)
