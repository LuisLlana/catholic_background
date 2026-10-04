// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later
package es.llana.catholicbackground.work

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import es.llana.catholicbackground.data.Settings
import es.llana.catholicbackground.wallpaper.WallpaperUpdater

/** Periodic check: changes the wallpaper when the server has a different image. */
class UpdateWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result {
        if (!Settings(applicationContext).autoWallpaper) return Result.success()
        WallpaperUpdater(applicationContext).update(force = false, automatic = true)
        return Result.success()
    }
}
