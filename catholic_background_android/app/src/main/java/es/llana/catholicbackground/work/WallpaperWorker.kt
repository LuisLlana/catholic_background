// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later
package es.llana.catholicbackground.work

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import es.llana.catholicbackground.wallpaper.WallpaperUpdater

/** Every hour, while this application keeps the wallpaper up to date: puts the new image, if any. */
class WallpaperWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result {
        WallpaperUpdater(applicationContext).keepUpToDate()
        Scheduler.scheduleWallpaper(applicationContext)   // stops if it is no longer followed
        return Result.success()
    }
}
