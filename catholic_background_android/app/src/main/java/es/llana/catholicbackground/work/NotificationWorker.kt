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
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import es.llana.catholicbackground.R
import es.llana.catholicbackground.data.ServerClient
import es.llana.catholicbackground.data.ServerException
import es.llana.catholicbackground.data.Settings
import es.llana.catholicbackground.ui.MainActivity
import java.time.LocalDate

/** Daily notification with the artwork of the day; tapping it opens the application. */
class NotificationWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result {
        val settings = Settings(applicationContext)
        try {
            val url = ServerClient.requestUrl(settings.serverUrl, LocalDate.now(), settings.languageCode(), label = false)
            notify(applicationContext, ServerClient.fetchArtwork(url))
        } catch (e: ServerException) {
            // No image today or server unreachable: no notification
        } finally {
            Scheduler.scheduleNotification(applicationContext)   // tomorrow
        }
        return Result.success()
    }

    companion object {
        const val CHANNEL = "daily"
        private const val ID = 1

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
