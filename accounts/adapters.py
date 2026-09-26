# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.contrib.auth.models import Group


def apply_automatic_roles(user):
    """Administrators from ADMIN_EMAILS, editors from AUTO_APPROVE_DOMAINS; everybody else waits."""
    email = (user.email or "").lower()
    changed = False
    if email and email in settings.ADMIN_EMAILS and not (user.is_staff and user.is_superuser):
        user.is_staff = user.is_superuser = True
        changed = True
    elif email and email.rsplit("@", 1)[-1] in settings.AUTO_APPROVE_DOMAINS and not user.is_staff:
        user.is_staff = True
        changed = True
        user.save(update_fields=["is_staff"])
        group, _ = Group.objects.get_or_create(name="Editors")
        user.groups.add(group)
        return
    if changed:
        user.save(update_fields=["is_staff", "is_superuser"])


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        apply_automatic_roles(user)
        return user
