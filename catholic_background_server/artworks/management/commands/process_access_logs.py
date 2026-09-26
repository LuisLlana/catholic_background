# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Aggregates the access logs into daily statistics (without IP addresses) and deletes
the logs older than ACCESS_LOG_DAYS. Run it once a day (see deploy/).
"""
from datetime import timedelta

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
