# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Everything hangs from BASE_PATH, read from the environment in settings.py
(os.environ["BASE_PATH"], "background" if it is not set):
    /<BASE_PATH>              the image of the day (the address used by the applications)
    /<BASE_PATH>/home/        start page after logging in
    /<BASE_PATH>/admin/       content management
    /<BASE_PATH>/accounts/    login with Google or Microsoft
    /<BASE_PATH>/privacy/     privacy policy
    /<BASE_PATH>/media/       uploaded images (editors only)
    /<BASE_PATH>/i18n/        language selector
"""
from allauth.account.decorators import secure_admin_login
from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.utils.translation import gettext_lazy as _

from accounts import views as account_views
from artworks import views as artwork_views

# The admin site uses the Google/Microsoft login, never a password form
admin.site.login = secure_admin_login(admin.site.login)
admin.site.site_header = "Catholic Background"
admin.site.site_title = "Catholic Background"
admin.site.index_title = _("Content management")
admin.site.site_url = f"{settings.PREFIX}privacy/"

pages = [
    path("", artwork_views.background),          # also answers /background/
    path("home/", account_views.home, name="home"),
    path("privacy/", artwork_views.privacy, name="privacy"),
    path("media/<path:path>", artwork_views.protected_media, name="media"),
    path("accounts/", include("allauth.urls")),
    path("i18n/", include("django.conf.urls.i18n")),     # set_language: the language selector
    path("admin/", admin.site.urls),
]

if settings.BASE_PATH:
    urlpatterns = [
        path(settings.BASE_PATH, artwork_views.background, name="background"),
        path(f"{settings.BASE_PATH}/", include(pages)),
    ]
else:
    urlpatterns = [path("", artwork_views.background, name="background")] + pages[1:]
