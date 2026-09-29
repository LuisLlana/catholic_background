# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
import base64
import io
import shutil
import tempfile
import time
from datetime import date, datetime, timedelta, timezone

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from accounts.adapters import apply_automatic_roles
from artworks import liturgy
from artworks.models import (AccessLog, Artwork, ArtworkMetadata, ArtworkTranslation, Celebration, Condition,
                             DailyStatistic, Language, MetadataKey, MetadataKeyName)
from artworks.selection import candidates, pick

MEDIA = tempfile.mkdtemp()
PREFIX = settings.PREFIX


def image_file(width=1600, height=1000, fmt="JPEG", name="artwork.jpg"):
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (120, 30, 60)).save(buffer, fmt)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")


def spanish():
    return Language.objects.get(code="es")


def english():
    return Language.objects.get(code="en")


def make_artwork(title, *conditions, approved=True):
    artwork = Artwork.objects.create(image=image_file(), approved=approved)
    ArtworkTranslation.objects.create(artwork=artwork, language=spanish(), title=title)
    for fields in conditions:
        Condition.objects.create(artwork=artwork, **fields)
    return artwork


def management(prefix, total, initial):
    """Management form of an admin inline formset."""
    return {f"{prefix}-TOTAL_FORMS": str(total), f"{prefix}-INITIAL_FORMS": str(initial),
            f"{prefix}-MIN_NUM_FORMS": "0", f"{prefix}-MAX_NUM_FORMS": "1000"}


def local_midnight_ts(day, utc_offset_hours=2):
    return int(datetime(day.year, day.month, day.day, tzinfo=timezone(timedelta(hours=utc_offset_hours))).timestamp())


class LiturgyTests(TestCase):
    def test_easter(self):
        for year, expected in [(2024, date(2024, 3, 31)), (2025, date(2025, 4, 20)), (2026, date(2026, 4, 5)),
                               (2027, date(2027, 3, 28)), (2038, date(2038, 4, 25))]:
            self.assertEqual(liturgy.easter(year), expected)

    def test_movable_dates_2026_spain(self):
        m = liturgy.movable_dates(2026)
        self.assertEqual(m["ash_wednesday"], date(2026, 2, 18))
        self.assertEqual(m["palm_sunday"], date(2026, 3, 29))
        self.assertEqual(m["ascension"], date(2026, 5, 17))       # Sunday in Spain
        self.assertEqual(m["pentecost"], date(2026, 5, 24))
        self.assertEqual(m["corpus_christi"], date(2026, 6, 7))   # Sunday in Spain
        self.assertEqual(m["sacred_heart"], date(2026, 6, 12))
        self.assertEqual(m["christ_king"], date(2026, 11, 22))
        self.assertEqual(m["first_advent"], date(2026, 11, 29))
        self.assertEqual(m["holy_family"], date(2026, 12, 27))
        self.assertEqual(m["baptism"], date(2026, 1, 11))

    @override_settings(CATHOLIC_BACKGROUND={"ASCENSION_ON_SUNDAY": False, "CORPUS_ON_SUNDAY": False})
    def test_thursday_ascension_and_corpus(self):
        m = liturgy.movable_dates(2026)
        self.assertEqual(m["ascension"], date(2026, 5, 14))
        self.assertEqual(m["corpus_christi"], date(2026, 6, 4))

    def test_holy_family_when_christmas_is_sunday(self):
        self.assertEqual(liturgy.holy_family(2022), date(2022, 12, 30))

    def test_seasons(self):
        cases = {
            date(2026, 1, 5): {"christmas"}, date(2026, 1, 11): {"christmas"}, date(2026, 1, 12): {"ordinary"},
            date(2026, 2, 18): {"lent"}, date(2026, 3, 30): {"lent", "holy_week"}, date(2026, 4, 5): {"easter"},
            date(2026, 5, 24): {"easter"}, date(2026, 5, 25): {"ordinary"}, date(2026, 11, 29): {"advent"},
            date(2026, 12, 24): {"advent"}, date(2026, 12, 25): {"christmas"},
        }
        for day, expected in cases.items():
            self.assertEqual(liturgy.seasons_on(day), expected, day)


@override_settings(MEDIA_ROOT=MEDIA)
class SelectionTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def test_or_semantics(self):
        joseph = Celebration.objects.get(month=3, day=19)
        lent = make_artwork("Lent", {"type": "season", "season": "lent"})
        saint = make_artwork("Saint Joseph", {"type": "saint", "celebration": joseph})
        both = make_artwork("Two conditions", {"type": "yearly_date", "month": 12, "day": 8},
                            {"type": "season", "season": "lent"})
        make_artwork("Advent", {"type": "season", "season": "advent"})
        make_artwork("Not approved", {"type": "season", "season": "lent"}, approved=False)
        self.assertEqual(candidates(date(2026, 3, 19)), [lent, saint, both])
        # 8 December is in Advent: the Advent artwork is also a candidate
        self.assertEqual([str(a) for a in candidates(date(2026, 12, 8))], ["Two conditions", "Advent"])

    def test_movable_celebration(self):
        pentecost = Celebration.objects.get(movable="pentecost")
        artwork = make_artwork("Pentecost", {"type": "celebration", "celebration": pentecost})
        self.assertEqual(candidates(date(2026, 5, 24)), [artwork])
        self.assertEqual(candidates(date(2027, 5, 16)), [artwork])

    def test_specific_date_and_reserve(self):
        reserve = make_artwork("Reserve", {"type": "any"})
        special = make_artwork("One day", {"type": "date", "date": date(2026, 10, 1)})
        self.assertEqual(candidates(date(2026, 10, 1)), [special])
        self.assertEqual(candidates(date(2026, 10, 2)), [reserve])

    def test_rotation_during_the_day(self):
        a = make_artwork("A", {"type": "any"})
        b = make_artwork("B", {"type": "any"})
        c = make_artwork("C", {"type": "any"})
        day = date(2026, 10, 2)
        self.assertEqual([pick(day, h * 3600) for h in (0, 7, 8, 15, 16, 23)], [a, a, b, b, c, c])


@override_settings(MEDIA_ROOT=MEDIA)
class ApiTests(TestCase):
    def test_background(self):
        key = MetadataKey.objects.create(name="Museum")
        artwork = make_artwork("The Annunciation", {"type": "any"})
        artwork.translations.update(author="Fra Angelico", year="c. 1426", description="The angel and the Virgin.")
        ArtworkMetadata.objects.create(artwork=artwork, key=key, language=spanish(), value="Museo del Prado")

        ts = local_midnight_ts(date.today())
        response = self.client.get(reverse("background"), {"ts": ts, "caption": "0"}, HTTP_USER_AGENT="test-agent")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "no-store")
        data = response.json()
        self.assertEqual((data["title"], data["author"], data["date"]), ("The Annunciation", "Fra Angelico", "c. 1426"))
        self.assertEqual(data["extra"], {"Museum": "Museo del Prado"})
        with Image.open(io.BytesIO(base64.b64decode(data["image"]))) as image:
            self.assertEqual(image.size, (1600, 1000))
        self.assertEqual(AccessLog.objects.get().user_agent, "test-agent")

    def test_errors(self):
        self.assertEqual(self.client.get(reverse("background"), {"ts": "abc"}).status_code, 400)
        self.assertEqual(self.client.get(reverse("background"), {"ts": 10 ** 20}).status_code, 400)
        self.assertEqual(self.client.get(reverse("background")).status_code, 404)   # no artworks

    def test_access_logs_become_statistics(self):
        artwork = make_artwork("A", {"type": "any"})
        old_day = date.today() - timedelta(days=40)
        old = AccessLog.objects.create(day=old_day, ip="10.0.0.1", artwork=artwork)
        AccessLog.objects.filter(pk=old.pk).update(created_at=datetime.now(timezone.utc) - timedelta(days=40))
        AccessLog.objects.create(day=date.today(), ip="10.0.0.2", artwork=artwork)
        call_command("process_access_logs", stdout=io.StringIO())
        self.assertEqual(AccessLog.objects.count(), 1)
        self.assertEqual(DailyStatistic.objects.get().clients, 1)


@override_settings(MEDIA_ROOT=MEDIA)
class ValidationTests(TestCase):
    def test_image_rules(self):
        from django.core.exceptions import ValidationError

        from artworks.validators import validate_image

        validate_image(image_file())
        with self.assertRaises(ValidationError):
            validate_image(image_file(400, 300))
        buffer = io.BytesIO()
        Image.new("RGB", (1600, 1000)).save(buffer, "GIF")
        with self.assertRaises(ValidationError):
            validate_image(SimpleUploadedFile("x.gif", buffer.getvalue()))

    def test_condition_needs_its_field(self):
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            Condition(type="season").clean()
        condition = Condition(type="season", season="lent", month=3, day=4)
        condition.clean()
        self.assertIsNone(condition.month)   # fields of other types are cleared


@override_settings(MEDIA_ROOT=MEDIA, ADMIN_EMAILS=["jefe@example.com"], AUTO_APPROVE_DOMAINS=["ucm.es"])
class AccessTests(TestCase):
    def test_automatic_roles(self):
        User = get_user_model()
        boss = User.objects.create(username="boss", email="jefe@example.com")
        editor = User.objects.create(username="ed", email="ana@ucm.es")
        stranger = User.objects.create(username="x", email="x@gmail.com")
        for user in (boss, editor, stranger):
            apply_automatic_roles(user)
            user.refresh_from_db()
        self.assertTrue(boss.is_superuser)
        self.assertTrue(editor.is_staff and editor.groups.filter(name="Editors").exists())
        self.assertFalse(stranger.is_staff)

    def test_pending_page_and_admin_login_redirect(self):
        user = get_user_model().objects.create(username="x", email="x@gmail.com")
        admin_url = f"{PREFIX}admin/"
        self.assertRedirects(self.client.get(admin_url), f"{admin_url}login/?next={admin_url}", fetch_redirect_response=False)
        self.client.force_login(user)
        self.assertContains(self.client.get(f"{PREFIX}home/"), "Waiting for approval")

    @override_settings(PASSWORD_LOGIN=False, SOCIALACCOUNT_ONLY=True)
    def test_no_password_login_when_disabled(self):
        response = self.client.get(reverse("account_login"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'type="password"')
        self.client.post(reverse("account_login"), {"login": "a@b.c", "password": "x"})
        self.assertNotIn("_auth_user_id", self.client.session)

    @override_settings(PASSWORD_LOGIN=True, SOCIALACCOUNT_ONLY=False,
                       ACCOUNT_SIGNUP_FIELDS=["email*", "password1*", "password2*"])
    def test_password_login(self):
        User = get_user_model()
        User.objects.create_user("luis", "luis@example.com", "a-long-password-123", is_staff=True)
        User.objects.create_user("new", "new@example.com", "another-password-456")
        page = self.client.get(reverse("account_login"))
        self.assertContains(page, 'type="password"')
        wrong = self.client.post(reverse("account_login"), {"login": "luis@example.com", "password": "bad"})
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(wrong.status_code, 200)
        response = self.client.post(reverse("account_login"), {"login": "luis@example.com", "password": "a-long-password-123"})
        self.assertRedirects(response, reverse("home"), fetch_redirect_response=False)
        self.assertRedirects(self.client.get(reverse("home")), reverse("admin:index"), fetch_redirect_response=False)
        self.client.logout()
        # A user without permissions waits for approval
        self.client.post(reverse("account_login"), {"login": "new@example.com", "password": "another-password-456"})
        self.assertContains(self.client.get(reverse("home")), "Waiting for approval")

    @override_settings(PASSWORD_LOGIN=True, SOCIALACCOUNT_ONLY=False,
                       ACCOUNT_SIGNUP_FIELDS=["email*", "password1*", "password2*"])
    def test_no_self_signup(self):
        response = self.client.post(reverse("account_signup"), {"email": "x@example.com", "password1": "p4ssw0rd-long!", "password2": "p4ssw0rd-long!"})
        self.assertFalse(get_user_model().objects.filter(email="x@example.com").exists())
        self.assertIn(response.status_code, (200, 302))

    def test_editor_changes_need_review(self):
        editor = get_user_model().objects.create(username="ed", email="ana@ucm.es", is_staff=True)
        editor.groups.add(Group.objects.get(name="Editors"))
        artwork = make_artwork("Approved", {"type": "any"})
        self.client.force_login(editor)
        url = reverse("admin:artworks_artwork_change", args=[artwork.pk])
        page = self.client.get(url)
        self.assertEqual(page.status_code, 200)
        condition = artwork.conditions.get()
        translation = artwork.translations.get()
        response = self.client.post(url, {
            "source_url": "",
            **management("translations", total=2, initial=1),
            "translations-0-id": str(translation.pk), "translations-0-artwork": str(artwork.pk),
            "translations-0-language": str(spanish().pk), "translations-0-title": "Changed",
            "translations-1-language": str(english().pk),          # empty block: not saved
            **management("conditions", total=1, initial=1),
            "conditions-0-id": str(condition.pk), "conditions-0-artwork": str(artwork.pk), "conditions-0-type": "any",
            **management("metadata", total=0, initial=0),
        })
        self.assertEqual(response.status_code, 302, getattr(response, "context_data", {}).get("errors"))
        artwork.refresh_from_db()
        self.assertEqual(str(artwork), "Changed")
        self.assertEqual(artwork.translations.count(), 1)
        self.assertFalse(artwork.approved)

    def test_drop_area_in_the_artwork_form(self):
        admin = get_user_model().objects.create(username="admin", email="jefe@example.com", is_staff=True, is_superuser=True)
        self.client.force_login(admin)
        page = self.client.get(reverse("admin:artworks_artwork_add"))
        self.assertContains(page, "data-cb-drop")
        self.assertContains(page, 'accept="image/jpeg,image/png"')
        artwork = make_artwork("A", {"type": "any"})
        page = self.client.get(reverse("admin:artworks_artwork_change", args=[artwork.pk]))
        self.assertContains(page, f'src="{artwork.image.url}"')   # current image shown in the area

    def add_artwork_through_admin(self, user, approved):
        self.client.force_login(user)
        data = {
            "image": image_file(), "source_url": "",
            **management("translations", total=2, initial=0),
            "translations-0-language": str(spanish().pk), "translations-0-title": f"By {user.username}",
            "translations-1-language": str(english().pk),
            **management("conditions", total=1, initial=0), "conditions-0-type": "any",
            **management("metadata", total=0, initial=0),
        }
        if approved:
            data["approved"] = "on"
        response = self.client.post(reverse("admin:artworks_artwork_add"), data)
        self.assertEqual(response.status_code, 302, getattr(response, "context_data", {}).get("errors"))
        return Artwork.objects.get(translations__title=f"By {user.username}")

    def test_reviewer_uploads_are_approved_by_default(self):
        User = get_user_model()
        reviewer = User.objects.create(username="rev", email="rev@ucm.es", is_staff=True)
        reviewer.groups.add(Group.objects.get(name="Reviewers"))
        editor = User.objects.create(username="ed", email="ed@ucm.es", is_staff=True)
        editor.groups.add(Group.objects.get(name="Editors"))

        # The reviewer sees the box already ticked
        self.client.force_login(reviewer)
        page = self.client.get(reverse("admin:artworks_artwork_add"))
        self.assertContains(page, 'name="approved" id="id_approved" checked')
        artwork = self.add_artwork_through_admin(reviewer, approved=True)
        self.assertTrue(artwork.approved)
        self.assertEqual(artwork.approved_by, reviewer)
        self.assertIsNotNone(artwork.approved_at)

        # ...but can leave it pending
        reviewer.username = "rev2"
        reviewer.save()
        pending = self.add_artwork_through_admin(reviewer, approved=False)
        self.assertFalse(pending.approved)
        self.assertIsNone(pending.approved_by)

        # Editors' uploads are still pending, even if they send the box
        by_editor = self.add_artwork_through_admin(editor, approved=True)
        self.assertFalse(by_editor.approved)

    def test_admin_pages(self):
        admin = get_user_model().objects.create(username="admin", email="jefe@example.com", is_staff=True, is_superuser=True)
        make_artwork("A", {"type": "any"})
        self.client.force_login(admin)
        for url in ("admin/", "admin/artworks/artwork/", "admin/artworks/artwork/add/", "admin/artworks/artwork/calendar/",
                    "admin/artworks/celebration/", "admin/artworks/metadatakey/", "privacy/"):
            self.assertEqual(self.client.get(PREFIX + url).status_code, 200, url)

    def test_everything_hangs_from_the_base_path(self):
        image_url = PREFIX.rstrip("/") or "/"
        self.assertEqual(reverse("background"), image_url)
        for name in ("home", "privacy", "account_login", "admin:index"):
            self.assertTrue(reverse(name).startswith(PREFIX), name)
        self.assertTrue(settings.STATIC_URL.startswith(PREFIX) and settings.MEDIA_URL.startswith(PREFIX))
        make_artwork("A", {"type": "any"})
        self.assertEqual(self.client.get(PREFIX).status_code, 200)             # /background/ also works
        self.assertEqual(self.client.get(image_url).status_code, 200)           # /background


@override_settings(MEDIA_ROOT=MEDIA)
class LanguageTests(TestCase):
    def test_language_from_the_browser(self):
        login = reverse("account_login")
        self.assertContains(self.client.get(login, HTTP_ACCEPT_LANGUAGE="es-ES,es;q=0.9"), 'lang="es"')
        self.assertContains(self.client.get(login, HTTP_ACCEPT_LANGUAGE="es-ES,es;q=0.9"), "Contraseña")
        self.assertContains(self.client.get(login, HTTP_ACCEPT_LANGUAGE="en-GB"), "Password")
        self.assertContains(self.client.get(login, HTTP_ACCEPT_LANGUAGE="fr-FR"), "Password")   # not available: English

    def test_language_selector_stores_a_cookie(self):
        login = reverse("account_login")
        self.assertContains(self.client.get(login), 'name="language"')          # the selector is there
        response = self.client.post(reverse("set_language"), {"language": "es", "next": login})
        self.assertRedirects(response, login, fetch_redirect_response=False)
        cookie = response.cookies[settings.LANGUAGE_COOKIE_NAME]
        self.assertEqual((cookie.value, cookie["path"]), ("es", PREFIX))
        # The cookie wins over the browser
        self.assertContains(self.client.get(login, HTTP_ACCEPT_LANGUAGE="en"), "Contraseña")

    def test_cookie_notice(self):
        login = reverse("account_login")
        self.assertContains(self.client.get(login), 'id="cb-cookies"')
        self.client.cookies["cookie_notice"] = "1"
        self.assertNotContains(self.client.get(login), 'id="cb-cookies"')

    def test_privacy_page_in_both_languages(self):
        self.assertContains(self.client.get(reverse("privacy"), HTTP_ACCEPT_LANGUAGE="es"), "Política de privacidad")
        page = self.client.get(reverse("privacy"), HTTP_ACCEPT_LANGUAGE="en")
        self.assertContains(page, "Privacy Policy")
        self.assertContains(page, 'id="cookies"')

    def test_admin_in_spanish(self):
        admin = get_user_model().objects.create(username="admin", email="a@example.com", is_staff=True, is_superuser=True)
        self.client.force_login(admin)
        joseph = Celebration.objects.get(month=3, day=19)
        make_artwork("Joseph", {"type": "saint", "celebration": joseph})
        spanish = {"HTTP_ACCEPT_LANGUAGE": "es"}
        self.assertContains(self.client.get(reverse("admin:index"), **spanish), "Gestión de contenidos")
        self.assertContains(self.client.get(reverse("admin:artworks_artwork_changelist"), **spanish), "San José, esposo de la Virgen María")
        self.assertContains(self.client.get(reverse("admin:artworks_artwork_add"), **spanish), "Arrastra una imagen aquí")
        self.assertContains(self.client.get(reverse("admin:artworks_calendar"), **spanish), "Calendario de los próximos días")
        self.assertContains(self.client.get(reverse("admin:artworks_artwork_changelist"), HTTP_ACCEPT_LANGUAGE="en"),
                            "Saint Joseph, Spouse of the Blessed Virgin Mary")

    def test_api_is_not_affected_by_the_language(self):
        make_artwork("A", {"type": "any"})
        data = self.client.get(reverse("background"), HTTP_ACCEPT_LANGUAGE="es").json()
        self.assertEqual(data["title"], "A")


@override_settings(MEDIA_ROOT=MEDIA)
class ContentLanguageTests(TestCase):
    def setUp(self):
        self.artwork = make_artwork("La Anunciación", {"type": "any"})
        self.artwork.translations.update(author="Fra Angelico", description="El ángel anuncia a María.", license="Dominio público")
        ArtworkTranslation.objects.create(artwork=self.artwork, language=english(), title="The Annunciation", license="Public domain")
        key = MetadataKey.objects.create(name="Museo")
        MetadataKeyName.objects.create(key=key, language=spanish(), name="Museo")
        MetadataKeyName.objects.create(key=key, language=english(), name="Museum")
        ArtworkMetadata.objects.create(artwork=self.artwork, key=key, language=spanish(), value="Museo del Prado")
        ArtworkMetadata.objects.create(artwork=self.artwork, key=key, language=english(), value="Prado Museum")

    def get(self, **kwargs):
        response = self.client.get(reverse("background"), **kwargs)
        return response, response.json()

    def test_initial_languages(self):
        self.assertEqual(list(Language.objects.values_list("code", flat=True)), ["es", "en"])
        self.assertEqual(Language.default().code, "es")

    def test_default_language(self):
        response, data = self.get()
        self.assertEqual((data["language"], data["title"], data["extra"]), ("es", "La Anunciación", {"Museo": "Museo del Prado"}))
        self.assertEqual(response["Content-Language"], "es")

    def test_requested_language_and_fallback_per_field(self):
        for kwargs in ({"data": {"lang": "en"}}, {"data": {"lang": "en-GB"}}, {"data": {"lang": "EN"}}):
            _, data = self.get(**kwargs)
            self.assertEqual(data["language"], "en", kwargs)
            self.assertEqual((data["title"], data["license"]), ("The Annunciation", "Public domain"))
            self.assertEqual(data["description"], "El ángel anuncia a María.")    # no English text: the default one
            self.assertEqual(data["author"], "Fra Angelico")
            self.assertEqual(data["extra"], {"Museum": "Prado Museum"})

    def test_unavailable_language(self):
        _, data = self.get(data={"lang": "fr-FR"})
        self.assertEqual((data["language"], data["title"]), ("es", "La Anunciación"))

    def test_accept_language_is_not_used(self):
        # The same request must give the same image whatever HTTP library the application uses
        _, data = self.get(HTTP_ACCEPT_LANGUAGE="en-GB,en;q=0.9")
        self.assertEqual(data["language"], "es")

    def test_new_language_added_by_the_administrator(self):
        french = Language.objects.create(code="fr", name="Français", order=2)
        ArtworkTranslation.objects.create(artwork=self.artwork, language=french, title="L'Annonciation")
        _, data = self.get(data={"lang": "fr"})
        self.assertEqual((data["language"], data["title"], data["license"]), ("fr", "L'Annonciation", "Dominio público"))

    def test_only_one_default_language(self):
        english_language = english()
        english_language.is_default = True
        english_language.save()
        self.assertEqual(list(Language.objects.filter(is_default=True).values_list("code", flat=True)), ["en"])

    def test_admin_form_has_one_block_per_language(self):
        admin = get_user_model().objects.create(username="admin", email="a@example.com", is_staff=True, is_superuser=True)
        self.client.force_login(admin)
        page = self.client.get(reverse("admin:artworks_artwork_add")).content.decode()
        self.assertIn(f'<option value="{spanish().pk}" selected>Español</option>', page)
        self.assertIn(f'<option value="{english().pk}" selected>English</option>', page)
        self.assertEqual(self.client.get(reverse("admin:artworks_language_changelist")).status_code, 200)

    def test_languages_are_managed_only_by_administrators(self):
        editor = get_user_model().objects.create(username="ed", email="ed@example.com", is_staff=True)
        editor.groups.add(Group.objects.get(name="Reviewers"))
        self.client.force_login(editor)
        self.assertEqual(self.client.get(reverse("admin:artworks_language_add")).status_code, 403)
        self.assertEqual(self.client.get(reverse("admin:artworks_artwork_add")).status_code, 200)


@override_settings(MEDIA_ROOT=MEDIA)
class ReasonTests(TestCase):
    def fetch(self, day, lang):
        ts = local_midnight_ts(day)
        from unittest import mock
        with mock.patch("artworks.views.time.time", return_value=ts + 12 * 3600):
            return self.client.get(reverse("background"), {"ts": ts, "lang": lang}).json()

    def test_saint_wins_over_season(self):
        joseph = Celebration.objects.get(month=3, day=19)
        make_artwork("Joseph", {"type": "saint", "celebration": joseph}, {"type": "season", "season": "lent"})
        data = self.fetch(date(2026, 3, 19), "es")
        self.assertEqual((data["reason"], data["reason_type"]), ("San José, esposo de la Virgen María", "saint"))
        data = self.fetch(date(2026, 3, 19), "en")
        self.assertEqual(data["reason"], "Saint Joseph, Spouse of the Blessed Virgin Mary")
        data = self.fetch(date(2026, 3, 10), "es")          # another day of Lent: the season
        self.assertEqual((data["reason"], data["reason_type"]), ("Cuaresma", "season"))
        self.assertEqual(self.fetch(date(2026, 3, 10), "en")["reason"], "Lent")

    def test_movable_celebration(self):
        pentecost = Celebration.objects.get(movable="pentecost")
        make_artwork("Pentecost", {"type": "celebration", "celebration": pentecost})
        data = self.fetch(date(2026, 5, 24), "es")
        self.assertEqual((data["reason"], data["reason_type"]), ("Pentecostés", "celebration"))

    def test_no_special_reason(self):
        make_artwork("Reserve", {"type": "any"})
        make_artwork("Date", {"type": "date", "date": date(2026, 10, 1)})
        for day in (date(2026, 10, 1), date(2026, 10, 2)):
            data = self.fetch(day, "es")
            self.assertEqual((data["reason"], data["reason_type"]), ("", ""))


@override_settings(MEDIA_ROOT=MEDIA)
class LabelTests(TestCase):
    def fetch(self, **params):
        data = self.client.get(reverse("background"), params).json()
        return data, base64.b64decode(data["image"])

    def test_label_below_the_artwork(self):
        artwork = make_artwork("La Anunciación", {"type": "any"})
        artwork.translations.update(author="Fra Angelico", year="c. 1426")
        _, labelled = self.fetch()
        with Image.open(io.BytesIO(labelled)) as image:
            width, height = image.size
            self.assertEqual(width, 1600)
            self.assertGreater(height, 1000)                          # the label is added below
            self.assertEqual(image.getpixel((5, height - 5)), image.getpixel((1595, height - 5)))   # a plain band
        _, plain = self.fetch(caption="0")
        with artwork.image.open("rb") as f:
            self.assertEqual(plain, f.read())                       # caption=0: the original file

    def test_same_request_same_bytes_and_one_image_per_language(self):
        artwork = make_artwork("La Anunciación", {"type": "any"})
        ArtworkTranslation.objects.create(artwork=artwork, language=english(), title="The Annunciation")
        _, first = self.fetch(lang="es")
        _, second = self.fetch(lang="es")
        _, english_image = self.fetch(lang="en")
        self.assertEqual(first, second)
        self.assertNotEqual(first, english_image)

    def test_changing_the_texts_changes_the_image(self):
        artwork = make_artwork("La Anunciación", {"type": "any"})
        _, before = self.fetch()
        artwork.translations.update(title="La Anunciación de Cortona")
        _, after = self.fetch()
        self.assertNotEqual(before, after)

    def test_no_texts_no_label(self):
        artwork = Artwork.objects.create(image=image_file(), approved=True)
        Condition.objects.create(artwork=artwork, type="any")
        _, data = self.fetch()
        with Image.open(io.BytesIO(data)) as image:
            self.assertEqual(image.size, (1600, 1000))

    @override_settings(CATHOLIC_BACKGROUND={**settings.CATHOLIC_BACKGROUND, "CAPTION_DEFAULT": False})
    def test_label_can_be_disabled_by_default(self):
        make_artwork("A", {"type": "any"})
        _, data = self.fetch()
        with Image.open(io.BytesIO(data)) as image:
            self.assertEqual(image.size, (1600, 1000))
        _, data = self.fetch(caption="1")
        with Image.open(io.BytesIO(data)) as image:
            self.assertGreater(image.size[1], 1000)


@override_settings(MEDIA_ROOT=MEDIA)
class OtherDaysAndEditTests(TestCase):
    def test_any_day_can_be_asked_for(self):
        make_artwork("Reserve", {"type": "any"})
        joseph = Celebration.objects.get(month=3, day=19)
        make_artwork("Joseph", {"type": "saint", "celebration": joseph})
        for day, title in ((date(1990, 3, 19), "Joseph"), (date(2040, 3, 19), "Joseph"), (date(2040, 3, 20), "Reserve")):
            response = self.client.get(reverse("background"), {"ts": local_midnight_ts(day), "caption": "0"})
            self.assertEqual(response.status_code, 200, day)
            self.assertEqual(response.json()["title"], title, day)

    def test_turns_follow_the_time_of_day_for_other_days(self):
        from unittest import mock
        first = make_artwork("First", {"type": "any"})
        second = make_artwork("Second", {"type": "any"})
        other_day = local_midnight_ts(date(2031, 5, 5))
        today = local_midnight_ts(date(2026, 9, 28))
        for hour, title in ((3, "First"), (15, "Second")):
            with mock.patch("artworks.views.time.time", return_value=today + hour * 3600):
                data = self.client.get(reverse("background"), {"ts": other_day, "caption": "0"}).json()
            self.assertEqual(data["title"], title, hour)

    def test_edit_link(self):
        artwork = make_artwork("A", {"type": "any"})
        data = self.client.get(reverse("background"), {"caption": "0"}).json()
        self.assertEqual(data["id"], artwork.pk)
        self.assertEqual(data["edit_url"], f"http://testserver{PREFIX}admin/artworks/artwork/{artwork.pk}/change/")

    def test_languages(self):
        Language.objects.create(code="fr", name="Français", order=5)
        data = self.client.get(reverse("languages")).json()
        self.assertEqual(data["default"], "es")
        self.assertEqual([l["code"] for l in data["languages"]], ["es", "en", "fr"])
        self.assertEqual(data["languages"][0]["name"], "Español")
        self.assertEqual(reverse("languages"), f"{PREFIX}languages")
