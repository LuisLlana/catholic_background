// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later
package es.llana.catholicbackground.work

import android.content.Context
import androidx.work.Constraints
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import es.llana.catholicbackground.data.Settings
import java.time.Duration
import java.time.LocalDateTime
import java.util.concurrent.TimeUnit

/** The daily notification (WorkManager survives reboots). The wallpaper is never changed in the background. */
object Scheduler {
    /** Periodic wallpaper check of versions up to 0.5.0, cancelled. */
    private const val OLD_UPDATE = "wallpaper-update"
    private const val NOTIFICATION = "daily-notification"

    private val network = Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build()

    fun scheduleAll(context: Context) {
        WorkManager.getInstance(context).cancelUniqueWork(OLD_UPDATE)
        scheduleNotification(context)
    }

    /** The next notification, at the chosen time (today if it has not passed yet, else tomorrow). */
    fun scheduleNotification(context: Context) {
        val settings = Settings(context)
        val manager = WorkManager.getInstance(context)
        if (!settings.notifications) {
            manager.cancelUniqueWork(NOTIFICATION)
            return
        }
        val now = LocalDateTime.now()
        var next = now.toLocalDate().atStartOfDay().plusMinutes(settings.notificationMinutes.toLong())
        if (!next.isAfter(now)) next = next.plusDays(1)
        val request = OneTimeWorkRequestBuilder<NotificationWorker>()
            .setInitialDelay(Duration.between(now, next).toMillis(), TimeUnit.MILLISECONDS)
            .setConstraints(network)
            .build()
        manager.enqueueUniqueWork(NOTIFICATION, ExistingWorkPolicy.REPLACE, request)
    }
}
