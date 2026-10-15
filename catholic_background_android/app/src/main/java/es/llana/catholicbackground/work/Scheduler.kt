// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later
package es.llana.catholicbackground.work

import android.app.AlarmManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import androidx.work.WorkManager
import es.llana.catholicbackground.data.Settings
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.ZoneId

/**
 * The daily notification, with an alarm of the system at the chosen time (setAndAllowWhileIdle:
 * it also goes off when the phone is idle, at most a few minutes late, and needs no permission).
 * The wallpaper is never changed in the background.
 */
object Scheduler {
    /** Work of older versions, cancelled: the periodic wallpaper check (up to 0.5.0) and the notification (up to 0.6.0). */
    private val OLD_WORK = listOf("wallpaper-update", "daily-notification")

    fun scheduleAll(context: Context) {
        val manager = WorkManager.getInstance(context)
        OLD_WORK.forEach { manager.cancelUniqueWork(it) }
        scheduleNotification(context)
    }

    /** Sets (or cancels) the alarm of the next notification. It can be called any number of times. */
    fun scheduleNotification(context: Context) {
        val settings = Settings(context)
        val alarms = context.getSystemService(AlarmManager::class.java)
        val intent = PendingIntent.getBroadcast(context, 0, Intent(context, AlarmReceiver::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        if (!settings.notifications) {
            alarms.cancel(intent)
            return
        }
        val next = nextTime(LocalDateTime.now(), settings.notificationMinutes, settings.lastAttemptDay)
        alarms.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, next.atZone(ZoneId.systemDefault()).toInstant().toEpochMilli(), intent)
    }

    /**
     * When the next notification goes: today at the chosen time if it has not passed yet; if it
     * passed and today's was not tried (the phone was off, the time was changed…), in a minute;
     * else tomorrow. lastAttempt: ISO date of the last notification tried, "" = never (just
     * installed: the first one is the next day at that time).
     */
    fun nextTime(now: LocalDateTime, minutes: Int, lastAttempt: String): LocalDateTime {
        val today = now.toLocalDate().atStartOfDay().plusMinutes(minutes.toLong())
        return when {
            now.isBefore(today) -> today
            lastAttempt.isNotEmpty() && lastAttempt != now.toLocalDate().toString() -> now.plusMinutes(1)
            else -> today.plusDays(1)
        }
    }

    fun today(): String = LocalDate.now().toString()
}
