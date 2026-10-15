// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later
package es.llana.catholicbackground.work

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import es.llana.catholicbackground.data.Settings
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.async
import kotlinx.coroutines.launch
import kotlinx.coroutines.withTimeoutOrNull

/**
 * The alarm of the daily notification: downloads the image of today and shows it at once; if the
 * server cannot be reached in a few seconds, WorkManager tries again when there is network.
 * Also sets the alarm again after a reboot, an update of the application or a change of the clock
 * (the system forgets the alarms then).
 */
class AlarmReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val app = context.applicationContext
        if (intent.action != null) {   // boot, update, clock or time zone changed
            Scheduler.scheduleNotification(app)
            return
        }
        Settings(app).lastAttemptDay = Scheduler.today()
        val pending = goAsync()
        scope.launch {
            try {
                // A receiver has about 10 seconds; the download may go on in the background
                val download = scope.async { NotificationWorker.notifyToday(app) }
                val done = withTimeoutOrNull(8_000) { runCatching { download.await() }.getOrDefault(false) }
                if (done != true) NotificationWorker.retryLater(app)
            } finally {
                Scheduler.scheduleNotification(app)   // tomorrow
                pending.finish()
            }
        }
    }

    companion object {
        private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    }
}
