# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Creates the languages Spanish (default) and English, and moves the existing texts,
which are in Spanish, to the new tables:
- title, author, year, comment and license of each artwork -> its Spanish texts;
- additional data -> marked as Spanish;
- names of the kinds of additional data -> their Spanish name.
"""
from django.db import migrations

TEXT_FIELDS = ("title", "author", "year", "description", "license")


def forwards(apps, schema_editor):
    db = schema_editor.connection.alias
    Language = apps.get_model("artworks", "Language")
    Artwork = apps.get_model("artworks", "Artwork")
    ArtworkTranslation = apps.get_model("artworks", "ArtworkTranslation")
    ArtworkMetadata = apps.get_model("artworks", "ArtworkMetadata")
    MetadataKey = apps.get_model("artworks", "MetadataKey")
    MetadataKeyName = apps.get_model("artworks", "MetadataKeyName")

    spanish, _ = Language.objects.using(db).get_or_create(
        code="es", defaults={"name": "Español", "order": 0, "is_default": True})
    Language.objects.using(db).get_or_create(code="en", defaults={"name": "English", "order": 1})

    for artwork in Artwork.objects.using(db).all():
        texts = {field: getattr(artwork, field) for field in TEXT_FIELDS}
        if any(texts.values()):
            ArtworkTranslation.objects.using(db).get_or_create(artwork=artwork, language=spanish, defaults=texts)
    ArtworkMetadata.objects.using(db).filter(language__isnull=True).update(language=spanish)
    for key in MetadataKey.objects.using(db).all():
        MetadataKeyName.objects.using(db).get_or_create(key=key, language=spanish, defaults={"name": key.name})


def backwards(apps, schema_editor):
    db = schema_editor.connection.alias
    Artwork = apps.get_model("artworks", "Artwork")
    ArtworkTranslation = apps.get_model("artworks", "ArtworkTranslation")
    for translation in ArtworkTranslation.objects.using(db).filter(language__code="es"):
        Artwork.objects.using(db).filter(pk=translation.artwork_id).update(
            **{field: getattr(translation, field) for field in TEXT_FIELDS})


class Migration(migrations.Migration):
    dependencies = [("artworks", "0007_languages")]
    operations = [migrations.RunPython(forwards, backwards)]
