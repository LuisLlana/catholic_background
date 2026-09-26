# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
from django.db import migrations


def load(apps, schema_editor):
    from artworks.data.celebrations import CELEBRATIONS

    Celebration = apps.get_model("artworks", "Celebration")
    db = schema_editor.connection.alias
    Celebration.objects.using(db).bulk_create([
        Celebration(name=name, kind=kind, rank=rank, month=month, day=day, movable=movable)
        for name, kind, rank, month, day, movable in CELEBRATIONS
    ])


def unload(apps, schema_editor):
    apps.get_model("artworks", "Celebration").objects.using(schema_editor.connection.alias).all().delete()


class Migration(migrations.Migration):
    dependencies = [("artworks", "0001_initial")]
    operations = [migrations.RunPython(load, unload)]
