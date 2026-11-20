# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Loads the texts of the artworks in a language from a JSON file (e.g. a translation):

    python manage.py import_texts translations-en.json --dry-run    # only says what it would do
    python manage.py import_texts translations-en.json

{
  "language": "en",
  "artworks": {
    "<id>": {
      "check_title": "<title in the default language>",     # skipped if it does not match
      "texts": {"title": …, "author": …, "year": …, "description": …, "license": …},
      "fix_default_language": {"<field>": {"from": "<current value>", "to": "<new value>"}}
    }
  },
  "metadata_keys": {"<internal name of the kind of data>": "<name in the language>"},
  "metadata": {"<id>": {"<internal name of the kind of data>": "<value in the language>"}}
}

Nothing written by hand is lost: a field is only filled in when it is empty in that language or
holds the same text as the default language (a copy that was never translated). A correction of
the default language is only made when the field still has the "from" value.
"""
import json

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from artworks.models import (TEXT_FIELDS, Artwork, ArtworkMetadata, ArtworkTranslation, Language, MetadataKey,
                             MetadataKeyName)


class Command(BaseCommand):
    help = "Load the texts of the artworks in a language (a translation) from a JSON file."

    def add_arguments(self, parser):
        parser.add_argument("file", help="JSON file with the texts")
        parser.add_argument("--dry-run", action="store_true", help="say what would change, without saving it")

    def handle(self, file, dry_run=False, **options):
        try:
            with open(file, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError) as error:
            raise CommandError(f"{file}: {error}")
        language = Language.objects.filter(code=data.get("language", "")).first()
        if language is None:
            raise CommandError(f"Language {data.get('language')!r} does not exist: add it in the content manager first.")
        default = Language.default()
        if default is None or default.pk == language.pk:
            raise CommandError("The texts must be in a language other than the default one.")
        self.counts = {"texts": 0, "fixes": 0, "kept": 0, "skipped": 0, "data": 0, "names": 0}
        with transaction.atomic():
            for pk, entry in data.get("artworks", {}).items():
                self.artwork(pk, entry, language, default)
            self.metadata(data, language, default)
            if dry_run:
                transaction.set_rollback(True)
        c = self.counts
        self.stdout.write(("Would change" if dry_run else "Changed") +
                          f": {c['texts']} fields of {language.name}, {c['fixes']} corrections of {default.name}, "
                          f"{c['data']} additional data, {c['names']} names of kinds of data. "
                          f"Kept as they were (already written by hand): {c['kept']}. Artworks skipped: {c['skipped']}.")

    def artwork(self, pk, entry, language, default):
        artwork = Artwork.objects.filter(pk=pk).first()
        original = ArtworkTranslation.objects.filter(artwork=artwork, language=default).first() if artwork else None
        if original is None or ("check_title" in entry and original.title != entry["check_title"]):
            self.counts["skipped"] += 1
            self.stderr.write(f"Artwork {pk}: not found or its title is not {entry.get('check_title')!r}; skipped.")
            return
        # Corrections of the default language first (e.g. a text written in the block of another language)
        changed = False
        for field, change in entry.get("fix_default_language", {}).items():
            if field in TEXT_FIELDS and getattr(original, field) == change.get("from"):
                setattr(original, field, change.get("to", ""))
                self.counts["fixes"] += 1
                changed = True
        if changed:
            original.save()

        translation, _ = ArtworkTranslation.objects.get_or_create(artwork=artwork, language=language)
        changed = False
        for field, value in entry.get("texts", {}).items():
            if field not in TEXT_FIELDS or not value:
                continue
            current = getattr(translation, field)
            if current == value:
                continue
            if current and current != getattr(original, field):
                self.counts["kept"] += 1
                continue
            setattr(translation, field, value)
            self.counts["texts"] += 1
            changed = True
        if changed:
            translation.full_clean()
            translation.save()

    def metadata(self, data, language, default):
        for key_name, name in data.get("metadata_keys", {}).items():
            key = MetadataKey.objects.filter(name=key_name).first()
            if key is None or not name:
                continue
            row, created = MetadataKeyName.objects.get_or_create(key=key, language=language, defaults={"name": name})
            if created:
                self.counts["names"] += 1
            elif not row.name:
                row.name = name
                row.save()
                self.counts["names"] += 1
        for pk, values in data.get("metadata", {}).items():
            for key_name, value in values.items():
                key = MetadataKey.objects.filter(name=key_name).first()
                if key is None or not value or not Artwork.objects.filter(pk=pk).exists():
                    continue
                original = ArtworkMetadata.objects.filter(artwork_id=pk, key=key, language=default).first()
                row = ArtworkMetadata.objects.filter(artwork_id=pk, key=key, language=language).first()
                if row is None:
                    ArtworkMetadata.objects.create(artwork_id=pk, key=key, language=language, value=value)
                elif row.value != value and (not row.value or (original and row.value == original.value)):
                    row.value = value
                    row.save()
                elif row.value != value:
                    self.counts["kept"] += 1
                    continue
                else:
                    continue
                self.counts["data"] += 1
