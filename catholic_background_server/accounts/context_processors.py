# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
from django.conf import settings


def login_options(request):
    return {"password_login": getattr(settings, "PASSWORD_LOGIN", False)}
