# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Fills the Spanish name of the celebrations of the initial catalogue (not the ones added by the users)."""
import importlib

from django.db import migrations

# The same (Spanish, English) pairs used to translate the catalogue to English
NAMES = importlib.import_module("artworks.migrations.0004_english_names").CELEBRATIONS


def fill(apps, schema_editor):
    Celebration = apps.get_model("artworks", "Celebration")
    db = schema_editor.connection.alias
    for spanish, english in NAMES:
        Celebration.objects.using(db).filter(name=english, name_es="").update(name_es=spanish)


class Migration(migrations.Migration):
    dependencies = [("artworks", "0005_celebration_name_es")]
    operations = [migrations.RunPython(fill, migrations.RunPython.noop)]
