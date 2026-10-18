// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later
package es.llana.catholicbackground.wallpaper

import android.app.WallpaperManager
import android.content.Context
import android.graphics.BitmapFactory
import android.os.Build
import android.util.Size
import android.view.WindowManager
import es.llana.catholicbackground.R
import es.llana.catholicbackground.data.Artwork
import es.llana.catholicbackground.data.ServerClient
import es.llana.catholicbackground.data.ServerException
import es.llana.catholicbackground.data.Settings
import es.llana.catholicbackground.ui.problemText
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import java.io.IOException
import java.time.LocalDate

/** Downloads the image of a day, composes it for the screen and sets it as wallpaper. */
class WallpaperUpdater(private val context: Context) {
    private val settings = Settings(context)

    /**
     * Sets the image of day as the wallpaper of target: "home", "lock" or "both", when the user
     * asks for it. From then on, keepUpToDate() changes it when there is a new image.
     * Returns (ok, message).
     */
    suspend fun set(day: LocalDate, target: String): Pair<Boolean, String> = lock.withLock {
        try {
            val url = ServerClient.requestUrl(settings.serverUrl, day, settings.languageCode(), settings.showLabel)
            apply(day, target, ServerClient.fetchArtwork(url))
            true to context.getString(R.string.result_updated)
        } catch (e: ServerException) {
            false to problemText(context, e)
        } catch (e: IOException) {
            false to context.getString(R.string.result_failed, e.message ?: "")
        } catch (e: SecurityException) {
            false to context.getString(R.string.result_failed, e.message ?: "")
        }
    }

    /**
     * Periodic check: if this application set the wallpaper (and the user did not put another
     * one since), it puts the image of today when it changes: a new day, or a new image of the
     * same day. A day chosen by hand stays until the next day. Returns true if it changed it.
     */
    suspend fun keepUpToDate(): Boolean = lock.withLock {
        val target = settings.followTarget
        if (target !in Settings.TARGETS) return@withLock false
        if (changedElsewhere(target)) {
            settings.followTarget = ""   // the user put another wallpaper: leave it
            return@withLock false
        }
        val today = LocalDate.now()
        try {
            val url = ServerClient.requestUrl(settings.serverUrl, today, settings.languageCode(), settings.showLabel)
            val artwork = ServerClient.fetchArtwork(url)
            if (!needsUpdate(today, settings.lastSetOn, settings.lastSetDay, settings.lastSetHash, artwork.hash)) {
                return@withLock false
            }
            apply(today, target, artwork)
            true
        } catch (e: ServerException) {
            false   // no image today or server down: the wallpaper is kept
        } catch (e: IOException) {
            false
        } catch (e: SecurityException) {
            false
        }
    }

    private suspend fun apply(day: LocalDate, target: String, artwork: Artwork) {
        setWallpaper(artwork.bytes, target)
        settings.lastSetDay = day.toString()
        settings.lastSetOn = LocalDate.now().toString()
        settings.lastSetHash = artwork.hash
        settings.followTarget = target
        val manager = WallpaperManager.getInstance(context)
        settings.homeWallpaperId = if (target != "lock") manager.getWallpaperId(WallpaperManager.FLAG_SYSTEM) else -1
        settings.lockWallpaperId = if (target != "home") manager.getWallpaperId(WallpaperManager.FLAG_LOCK) else -1
    }

    /** The wallpaper of target is not the one this application set: the user changed it. */
    private fun changedElsewhere(target: String): Boolean {
        val manager = WallpaperManager.getInstance(context)
        fun differs(flag: Int, saved: Int) = saved != -1 && manager.getWallpaperId(flag).let { it != -1 && it != saved }
        return (target != "lock" && differs(WallpaperManager.FLAG_SYSTEM, settings.homeWallpaperId)) ||
            (target != "home" && differs(WallpaperManager.FLAG_LOCK, settings.lockWallpaperId))
    }

    private suspend fun setWallpaper(bytes: ByteArray, where: String) = withContext(Dispatchers.Default) {
        val image = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
            ?: throw IOException(context.getString(R.string.problem_invalid_answer))
        val size = screenSize()
        val composed = Composer.compose(image, size.width, size.height, settings.background,
            Composer.parseColor(settings.backgroundColor))
        image.recycle()
        val flags = when (where) {
            "home" -> WallpaperManager.FLAG_SYSTEM
            "lock" -> WallpaperManager.FLAG_LOCK
            else -> WallpaperManager.FLAG_SYSTEM or WallpaperManager.FLAG_LOCK
        }
        WallpaperManager.getInstance(context).setBitmap(composed, null, true, flags)
        composed.recycle()
    }

    /** Size of the whole screen in pixels (portrait). */
    private fun screenSize(): Size {
        val windowManager = context.getSystemService(WindowManager::class.java)
        val (w, h) = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            windowManager.maximumWindowMetrics.bounds.let { it.width() to it.height() }
        } else {
            @Suppress("DEPRECATION")
            android.util.DisplayMetrics().also { windowManager.defaultDisplay.getRealMetrics(it) }.let { it.widthPixels to it.heightPixels }
        }
        return Size(minOf(w, h), maxOf(w, h))
    }

    companion object {
        /**
         * Whether the image of today (hash) must replace the wallpaper set on lastSetOn with the
         * image of lastSetDay (lastSetHash): always on another day; the same day, only if it was
         * today's image and the server has a different one (a day chosen by hand stays).
         */
        fun needsUpdate(today: LocalDate, lastSetOn: String, lastSetDay: String, lastSetHash: String, hash: String): Boolean {
            if (lastSetOn != today.toString()) return true
            return lastSetDay == today.toString() && hash != lastSetHash
        }

        /** One wallpaper at a time. */
        private val lock = Mutex()
    }
}
