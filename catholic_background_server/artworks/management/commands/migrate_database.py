# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Copies all the data to another database (e.g. from SQLite to PostgreSQL or MariaDB):

    python manage.py migrate_database postgres://user:password@host/catholic

Then set DATABASE_URL to the new database. Uploaded images are files and do not move.
"""
import tempfile

import dj_database_url
from django.apps import apps
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.core.management.color import no_style
from django.db import connections


KEEP = ("contenttypes.ContentType", "auth.Permission")


class Command(BaseCommand):
    help = "Copy all the data of this installation to another (empty) database."

    def add_arguments(self, parser):
        parser.add_argument("target_url", help="DATABASE_URL of the new database")

    def handle(self, target_url, **options):
        connections.databases["target"] = {**connections.databases["default"], **dj_database_url.parse(target_url)}
        target = connections["target"]
        if "artworks_artwork" in target.introspection.table_names() and \
                apps.get_model("artworks", "Artwork").objects.using("target").exists():
            raise CommandError("The new database already has artworks: use an empty database.")

        self.stdout.write("Creating the tables in the new database…")
        call_command("migrate", database="target", interactive=False, verbosity=0)

        models = [m for m in apps.get_models() if m._meta.managed and not m._meta.proxy]
        # migrate creates some rows (groups, initial calendar): replace them with the copied data.
        # Content types and permissions are kept: the copy refers to them by name.
        for model in models:
            if model._meta.label not in KEEP:
                model.objects.using("target").all().delete()

        with tempfile.NamedTemporaryFile(suffix=".json", mode="w+", encoding="utf-8") as dump:
            self.stdout.write("Copying the data…")
            call_command("dumpdata", natural_foreign=True, natural_primary=True,
                         exclude=["contenttypes", "auth.permission", "sessions"], output=dump.name, verbosity=0)
            call_command("loaddata", dump.name, database="target", verbosity=0)

        # PostgreSQL: update the id sequences after inserting explicit ids
        with connections["target"].cursor() as cursor:
            for sql in connections["target"].ops.sequence_reset_sql(no_style(), models):
                cursor.execute(sql)

        errors = []
        for model in models:
            if model._meta.label in ("contenttypes.ContentType", "auth.Permission", "sessions.Session"):
                continue
            source, target = model.objects.using("default").count(), model.objects.using("target").count()
            if source != target:
                errors.append(f"{model._meta.label}: {source} → {target}")
        if errors:
            raise CommandError("The counts do not match:\n" + "\n".join(errors))
        self.stdout.write(self.style.SUCCESS("Done. Now set DATABASE_URL to the new database."))
