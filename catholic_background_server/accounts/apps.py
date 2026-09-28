# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AccountsConfig(AppConfig):
    name = "accounts"
    verbose_name = _("Access")

    def ready(self):
        from django.contrib.auth.signals import user_logged_in

        from .adapters import apply_automatic_roles

        user_logged_in.connect(lambda sender, request, user, **kw: apply_automatic_roles(user), weak=False)
