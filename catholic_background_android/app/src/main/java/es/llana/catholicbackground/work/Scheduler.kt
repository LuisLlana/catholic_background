// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later
package es.llana.catholicbackground.work

import android.content.Context
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import es.llana.catholicbackground.data.Settings
import java.time.Duration
import java.time.LocalDateTime
import java.util.concurrent.TimeUnit

/** Background work: periodic wallpaper checks and the daily notification (WorkManager survives reboots). */
object Scheduler {
    private const val UPDATE = "wallpaper-update"
    private const val NOTIFICATION = "daily-notification"

    private val network = Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build()

    fun scheduleAll(context: Context, replace: Boolean = false) {
        scheduleUpdates(context, replace)
        scheduleNotification(context)
    }

    fun scheduleUpdates(context: Context, replace: Boolean = false) {
        val settings = Settings(context)
        val manager = WorkManager.getInstance(context)
        if (!settings.autoWallpaper) {
            manager.cancelUniqueWork(UPDATE)
            return
        }
        val request = PeriodicWorkRequestBuilder<UpdateWorker>(settings.checkIntervalMinutes.toLong(), TimeUnit.MINUTES)
            .setConstraints(network)
            .build()
        manager.enqueueUniquePeriodicWork(UPDATE,
            if (replace) ExistingPeriodicWorkPolicy.CANCEL_AND_REENQUEUE else ExistingPeriodicWorkPolicy.KEEP, request)
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
