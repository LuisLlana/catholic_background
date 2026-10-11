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
     * Sets the image of day as the wallpaper of target: "home", "lock" or "both".
     * Only when the user asks for it. Returns (ok, message).
     */
    suspend fun set(day: LocalDate, target: String): Pair<Boolean, String> = lock.withLock {
        try {
            val url = ServerClient.requestUrl(settings.serverUrl, day, settings.languageCode(), settings.showLabel)
            val artwork = ServerClient.fetchArtwork(url)
            setWallpaper(artwork.bytes, target)
            settings.lastSetDay = day.toString()
            true to context.getString(R.string.result_updated)
        } catch (e: ServerException) {
            false to problemText(context, e)
        } catch (e: IOException) {
            false to context.getString(R.string.result_failed, e.message ?: "")
        } catch (e: SecurityException) {
            false to context.getString(R.string.result_failed, e.message ?: "")
        }
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
        /** One wallpaper at a time. */
        private val lock = Mutex()
    }
}
