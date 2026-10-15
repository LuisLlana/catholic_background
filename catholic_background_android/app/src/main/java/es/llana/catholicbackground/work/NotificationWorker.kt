// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later
package es.llana.catholicbackground.work

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.BitmapFactory
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import androidx.core.graphics.scale
import androidx.work.BackoffPolicy
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import es.llana.catholicbackground.R
import es.llana.catholicbackground.data.ServerClient
import es.llana.catholicbackground.data.Problem
import es.llana.catholicbackground.data.ServerException
import es.llana.catholicbackground.data.Settings
import es.llana.catholicbackground.ui.MainActivity
import java.time.LocalDate
import java.util.concurrent.TimeUnit

/** Shows the notification of today when the alarm could not (no network then): WorkManager waits for it. */
class NotificationWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result = when {
        notifyToday(applicationContext) -> Result.success()
        runAttemptCount < 5 -> Result.retry()
        else -> Result.success()
    }

    companion object {
        const val CHANNEL = "daily"
        private const val ID = 1
        private const val RETRY = "notification-retry"

        /**
         * Downloads the image of today and shows the notification, once a day. True when it is
         * done (also when there is no image today); false if the server could not be reached.
         */
        suspend fun notifyToday(context: Context): Boolean {
            val settings = Settings(context)
            val today = Scheduler.today()
            if (settings.lastNotifiedDay == today) return true
            return try {
                val url = ServerClient.requestUrl(settings.serverUrl, LocalDate.now(), settings.languageCode(), label = false)
                notify(context, ServerClient.fetchArtwork(url))
                settings.lastNotifiedDay = today
                true
            } catch (e: ServerException) {
                if (e.problem == Problem.NO_IMAGE) settings.lastNotifiedDay = today
                e.problem == Problem.NO_IMAGE
            }
        }

        fun retryLater(context: Context) {
            val request = OneTimeWorkRequestBuilder<NotificationWorker>()
                .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
                .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 5, TimeUnit.MINUTES)
                .build()
            WorkManager.getInstance(context).enqueueUniqueWork(RETRY, ExistingWorkPolicy.KEEP, request)
        }

        /** Notifications of this application are allowed (permission and switch of the system). */
        fun allowed(context: Context): Boolean = NotificationManagerCompat.from(context).areNotificationsEnabled()

        fun createChannel(context: Context) {
            val channel = NotificationChannel(CHANNEL, context.getString(R.string.channel_name), NotificationManager.IMPORTANCE_DEFAULT)
                .apply { description = context.getString(R.string.channel_description) }
            context.getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
        }

        fun notify(context: Context, artwork: es.llana.catholicbackground.data.Artwork) {
            if (android.os.Build.VERSION.SDK_INT >= 33 &&
                ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                return
            }
            val open = PendingIntent.getActivity(context, 0,
                Intent(context, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP),
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
            val title = artwork.reason.ifEmpty { context.getString(R.string.notification_title) }
            val text = listOf(artwork.title, listOf(artwork.author, artwork.year).filter { it.isNotEmpty() }.joinToString(", "))
                .filter { it.isNotEmpty() }.joinToString(" — ")
            val builder = NotificationCompat.Builder(context, CHANNEL)
                .setSmallIcon(R.drawable.ic_notification)
                .setContentTitle(title)
                .setContentText(text)
                .setContentIntent(open)
                .setAutoCancel(true)
            BitmapFactory.decodeByteArray(artwork.bytes, 0, artwork.bytes.size)?.let { image ->
                val factor = minOf(1.0, 1024.0 / maxOf(image.width, image.height))
                val picture = if (factor < 1) image.scale((image.width * factor).toInt(), (image.height * factor).toInt()) else image
                builder.setLargeIcon(picture)
                    .setStyle(NotificationCompat.BigPictureStyle().bigPicture(picture).bigLargeIcon(null as android.graphics.Bitmap?)
                        .setSummaryText(text))
            }
            NotificationManagerCompat.from(context).notify(ID, builder.build())
        }
    }
}
