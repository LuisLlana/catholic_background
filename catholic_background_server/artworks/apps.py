# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
from django.apps import AppConfig
from django.db.models.signals import post_migrate


class ArtworksConfig(AppConfig):
    name = "artworks"
    verbose_name = "Content"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        post_migrate.connect(create_groups, sender=self)


EDITOR_PERMISSIONS = [
    "view_artwork", "add_artwork", "change_artwork", "delete_artwork",
    "view_condition", "add_condition", "change_condition", "delete_condition",
    "view_artworkmetadata", "add_artworkmetadata", "change_artworkmetadata", "delete_artworkmetadata",
    "view_metadatakey", "add_metadatakey",
    "view_celebration",
]
REVIEWER_PERMISSIONS = EDITOR_PERMISSIONS + [
    "approve_artwork", "change_metadatakey", "add_celebration", "change_celebration", "view_dailystatistic",
]


def create_groups(sender, using="default", **kwargs):
    """Groups 'Editors' (upload and edit) and 'Reviewers' (also approve and edit the calendar)."""
    from django.contrib.auth.models import Group, Permission

    for name, codenames in (("Editors", EDITOR_PERMISSIONS), ("Reviewers", REVIEWER_PERMISSIONS)):
        group, _ = Group.objects.using(using).get_or_create(name=name)
        permissions = Permission.objects.using(using).filter(content_type__app_label="artworks", codename__in=codenames)
        group.permissions.set(permissions)
