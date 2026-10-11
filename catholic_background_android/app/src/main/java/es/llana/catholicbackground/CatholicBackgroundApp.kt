// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later
package es.llana.catholicbackground

import android.app.Application
import es.llana.catholicbackground.work.NotificationWorker
import es.llana.catholicbackground.work.Scheduler

class CatholicBackgroundApp : Application() {
    override fun onCreate() {
        super.onCreate()
        NotificationWorker.createChannel(this)
        Scheduler.scheduleAll(this)
    }
}
