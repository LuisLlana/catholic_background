# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
from datetime import timedelta

from django.contrib import admin, messages
from django.db import models
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet
from django.template.response import TemplateResponse
from django.urls import path
from django.utils import timezone
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _
from PIL import Image

from . import liturgy
from .models import Artwork, ArtworkMetadata, Celebration, Condition, DailyStatistic, MetadataKey
from .selection import candidates, celebrations_on
from .widgets import DropImageWidget


class AtLeastOneConditionFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        kept = [f for f in self.forms
                if f.cleaned_data and not f.cleaned_data.get("DELETE") and f.cleaned_data.get("type")]
        if not kept:
            raise ValidationError(_("Say at least when the artwork is shown (it can be “Any day”)."))


class ConditionInline(admin.TabularInline):
    model = Condition
    formset = AtLeastOneConditionFormSet
    extra = 1
    fields = ["type", "season", "celebration", "month", "day", "date"]
    autocomplete_fields = ["celebration"]


class MetadataInline(admin.TabularInline):
    model = ArtworkMetadata
    extra = 1
    fields = ["key", "value"]


def can_approve(request):
    return request.user.has_perm("artworks.approve_artwork")


@admin.register(Artwork)
class ArtworkAdmin(admin.ModelAdmin):
    list_display = ["thumbnail", "__str__", "author", "year", "when", "approved"]
    list_display_links = ["thumbnail", "__str__"]
    list_filter = ["approved", "conditions__type", "conditions__season"]
    search_fields = ["title", "author", "year", "description", "metadata__value", "conditions__celebration__name",
                     "conditions__celebration__name_es"]
    inlines = [ConditionInline, MetadataInline]
    readonly_fields = ["approved_by", "approved_at", "created_by", "created_at", "updated_at"]
    fieldsets = [
        (None, {"fields": ["image"]}),
        (_("The artwork"), {"fields": ["title", "author", "year", "description"]}),
        (_("Source"), {"fields": ["source_url", "license"]}),
        (_("Review"), {"fields": ["approved", "approved_by", "approved_at", "created_by", "created_at", "updated_at"]}),
    ]
    actions = ["approve"]
    formfield_overrides = {models.ImageField: {"widget": DropImageWidget}}
    change_list_template = "admin/artworks/artwork/change_list.html"

    @admin.display(description=_("image"))
    def thumbnail(self, obj):
        return format_html('<img src="{}" style="height:60px;max-width:110px;object-fit:contain">', obj.image.url) if obj.image else ""

    @admin.display(description=_("when"))
    def when(self, obj):
        return "; ".join(str(c) for c in obj.conditions.all())

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("conditions__celebration")

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if not can_approve(request):
            fields.append("approved")
        return fields

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not can_approve(request):
            actions.pop("approve", None)
        return actions

    @admin.action(description=_("Approve the selected artworks"))
    def approve(self, request, queryset):
        count = queryset.filter(approved=False).update(approved=True, approved_by=request.user, approved_at=timezone.now())
        self.message_user(request, _("%(count)s artwork(s) approved.") % {"count": count})

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        # Artworks uploaded by a reviewer are approved by default (the box can be unticked)
        if can_approve(request):
            initial.setdefault("approved", True)
        return initial

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        if can_approve(request):
            if not obj.approved:
                obj.approved_by, obj.approved_at = None, None
            elif "approved" in form.changed_data or not obj.approved_by:
                obj.approved_by, obj.approved_at = request.user, timezone.now()
        elif change and form.changed_data:
            # A change by an editor must be reviewed again
            obj.approved, obj.approved_by, obj.approved_at = False, None, None
        super().save_model(request, obj, form, change)
        self.warn_about_shape(request, obj)

    def save_formset(self, request, form, formset, change):
        super().save_formset(request, form, formset, change)
        if change and formset.has_changed() and not can_approve(request) and form.instance.approved:
            Artwork.objects.filter(pk=form.instance.pk).update(approved=False, approved_by=None, approved_at=None)

    def warn_about_shape(self, request, obj):
        try:
            with Image.open(obj.image.path) as image:
                width, height = image.size
        except Exception:
            return
        if height > width * 1.6:
            messages.warning(request, _("The image is very tall: on screens it will look narrow, with a lot of filling at the sides."))
        elif width > height * 3:
            messages.warning(request, _("The image is very wide: on screens it will look low, with a lot of filling above and below."))

    # ------------------------------------------------ calendar of the next days
    def get_urls(self):
        return [path("calendar/", self.admin_site.admin_view(self.calendar_view), name="artworks_calendar")] + super().get_urls()

    def calendar_view(self, request):
        today = timezone.localdate()
        seasons = dict(liturgy.SEASONS)
        days = []
        for offset in range(int(request.GET.get("days", 60))):
            day = today + timedelta(days=offset)
            days.append({
                "date": day,
                "seasons": ", ".join(str(seasons[s]) for s in sorted(liturgy.seasons_on(day))),
                "celebrations": ", ".join(str(c) for c in celebrations_on(day)),
                "artworks": candidates(day),
            })
        context = {**self.admin_site.each_context(request), "title": _("Calendar of the next days"),
                   "days": days, "opts": self.model._meta}
        return TemplateResponse(request, "admin/artworks/artwork/calendar.html", context)


@admin.register(Celebration)
class CelebrationAdmin(admin.ModelAdmin):
    list_display = ["name", "name_es", "when", "kind", "rank"]
    list_filter = ["kind", "rank", "month"]
    search_fields = ["name", "name_es"]


@admin.register(MetadataKey)
class MetadataKeyAdmin(admin.ModelAdmin):
    list_display = ["name", "order"]
    list_editable = ["order"]
    search_fields = ["name"]


@admin.register(DailyStatistic)
class DailyStatisticAdmin(admin.ModelAdmin):
    list_display = ["day", "requests", "clients"]
    date_hierarchy = "day"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
