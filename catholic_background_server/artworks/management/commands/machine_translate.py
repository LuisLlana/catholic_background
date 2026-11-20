# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Translates in advance, with LibreTranslate, the texts of all the approved artworks, so that the
first visitor who asks for a language does not wait for the translation:

    python manage.py machine_translate --languages fr,it,pt
    python manage.py machine_translate --all        # every language LibreTranslate offers

Without it each text is translated the first time it is asked for. The reasons (saint, season
of the day) are short and are always translated when asked for.
"""
from django.core.management.base import BaseCommand, CommandError

from artworks import machine
from artworks.models import Artwork
from artworks.views import machine_languages


class Command(BaseCommand):
    help = "Translate in advance the texts of the artworks with LibreTranslate."

    def add_arguments(self, parser):
        parser.add_argument("--languages", default="", help="codes separated by commas (e.g. fr,it)")
        parser.add_argument("--all", action="store_true", help="every language LibreTranslate offers")

    def handle(self, languages="", all=False, **options):
        if not machine.enabled():
            raise CommandError("LIBRETRANSLATE_URL is not set.")
        offered = [code for code, _ in machine_languages()]
        if not offered:
            raise CommandError("LibreTranslate offers no language (is it running?).")
        wanted = offered if all else [code.strip() for code in languages.split(",") if code.strip()]
        if not wanted:
            raise CommandError("Say which languages (--languages fr,it) or --all.")
        unknown = [code for code in wanted if code not in offered]
        if unknown:
            raise CommandError(f"Not offered by LibreTranslate, or written by hand: {', '.join(unknown)}")
        artworks = list(Artwork.objects.filter(approved=True))
        for code in wanted:
            failed = 0
            for artwork in artworks:
                texts = artwork.texts()
                if machine.translate_artwork(texts, "", artwork.additional_data(), code) is None:
                    failed += 1
            self.stdout.write(f"{code}: {len(artworks) - failed} artworks translated" +
                              (f", {failed} could not be translated" if failed else "") + ".")
