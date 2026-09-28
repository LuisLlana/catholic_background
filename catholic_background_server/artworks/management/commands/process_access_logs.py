# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Aggregates the access logs into daily statistics (without IP addresses) and deletes
the logs older than ACCESS_LOG_DAYS. Run it once a day (see deploy/).
"""
import time
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Count
from django.utils import timezone

from artworks.models import AccessLog, DailyStatistic


class Command(BaseCommand):
    help = "Update daily statistics and delete old access logs (IP addresses)."

    def handle(self, *args, **options):
        today = timezone.localdate()
        rows = (AccessLog.objects.filter(day__lt=today)
                .values("day").annotate(requests=Count("id"), clients=Count("ip", distinct=True)))
        for row in rows:
            DailyStatistic.objects.update_or_create(day=row["day"], defaults={
                "requests": row["requests"], "clients": row["clients"]})
        limit = timezone.now() - timedelta(days=settings.CATHOLIC_BACKGROUND["ACCESS_LOG_DAYS"])
        deleted, _ = AccessLog.objects.filter(created_at__lt=limit).delete()
        self.stdout.write(f"Statistics updated; {deleted} old access log(s) deleted.")

        # Labelled images not served for a while (e.g. of artworks whose texts changed)
        cache = Path(settings.MEDIA_ROOT) / "caption-cache"
        oldest = time.time() - settings.CATHOLIC_BACKGROUND["CAPTION_CACHE_DAYS"] * 86400
        removed = 0
        for file in cache.glob("*.jpg") if cache.exists() else []:
            if file.stat().st_mtime < oldest:
                file.unlink(missing_ok=True)
                removed += 1
        self.stdout.write(f"{removed} old labelled image(s) removed from the cache.")
