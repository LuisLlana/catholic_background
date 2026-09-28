# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
from django.conf import settings


def login_options(request):
    return {"password_login": getattr(settings, "PASSWORD_LOGIN", False)}


def cookie_notice(request):
    """The cookie notice is shown until it is acknowledged (which stores a cookie)."""
    name = getattr(settings, "COOKIE_NOTICE_COOKIE", "cookie_notice")
    return {
        "cookie_notice_accepted": request.COOKIES.get(name) == "1",
        "cookie_notice_name": name,
        "cookie_path": getattr(settings, "PREFIX", "/"),
        "cookie_secure": getattr(settings, "SESSION_COOKIE_SECURE", False),
    }
