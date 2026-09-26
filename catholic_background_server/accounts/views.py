# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render


@login_required
def home(request):
    """After logging in: editors go to the admin site; new users wait for approval."""
    if request.user.is_staff and request.user.is_active:
        return redirect("admin:index")
    return render(request, "account/pending.html")
