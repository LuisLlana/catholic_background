# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
from django.urls import reverse

# Names of the URLs that search engines may index; everything else (content manager, login,
# home page, API, images) is answered with "X-Robots-Tag: noindex"
PUBLIC_PAGES = ("browser", "time", "privacy", "sitemap")


class NoIndexMiddleware:
    """Keeps out of search engines every page that is not public."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.public = None

    def __call__(self, request):
        response = self.get_response(request)
        if self.public is None:
            self.public = {reverse(name) for name in PUBLIC_PAGES}
        if request.path not in self.public:
            response.headers.setdefault("X-Robots-Tag", "noindex, nofollow")
        return response
