# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
from allauth.account.decorators import secure_admin_login
from django.contrib import admin
from django.urls import include, path

from accounts import views as account_views
from artworks import views as artwork_views

# The admin site uses the Google/Microsoft login, never a password form
admin.site.login = secure_admin_login(admin.site.login)
admin.site.site_header = "Catholic Background"
admin.site.site_title = "Catholic Background"
admin.site.index_title = "Gestión de contenidos"

urlpatterns = [
    path("", account_views.home, name="home"),
    path("background", artwork_views.background, name="background"),
    path("privacy/", artwork_views.privacy, name="privacy"),
    path("media/<path:path>", artwork_views.protected_media, name="media"),
    path("accounts/", include("allauth.urls")),
    path("admin/", admin.site.urls),
]
