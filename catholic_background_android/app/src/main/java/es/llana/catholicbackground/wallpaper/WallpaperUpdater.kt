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

/** Downloads the image of the wallpaper day, composes it for the screen and sets it. */
class WallpaperUpdater(private val context: Context) {
    private val settings = Settings(context)

    /**
     * force: set it even if it did not change. automatic: a periodic check, which also ends a day
     * chosen with "Use as wallpaper" (back to today). Returns (ok, message).
     */
    suspend fun update(force: Boolean, automatic: Boolean = false): Pair<Boolean, String> = lock.withLock {
        var force = force
        if (automatic && settings.showDate.isNotEmpty()) {
            settings.showDate = ""
            force = true
        }
        val result = try {
            val artwork = ServerClient.fetchArtwork(settings.wallpaperUrl())
            if (!force && artwork.hash == settings.imageHash) {
                true to context.getString(R.string.result_unchanged)
            } else {
                setWallpaper(artwork.bytes)
                settings.imageHash = artwork.hash
                true to context.getString(R.string.result_updated)
            }
        } catch (e: ServerException) {
            false to problemText(context, e)
        } catch (e: IOException) {
            false to context.getString(R.string.result_failed, e.message ?: "")
        } catch (e: SecurityException) {
            false to context.getString(R.string.result_failed, e.message ?: "")
        }
        settings.lastCheck = System.currentTimeMillis()
        settings.lastResult = result.second
        result
    }

    private suspend fun setWallpaper(bytes: ByteArray) = withContext(Dispatchers.Default) {
        val image = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
            ?: throw IOException(context.getString(R.string.problem_invalid_answer))
        val size = screenSize()
        val composed = Composer.compose(image, size.width, size.height, settings.background,
            Composer.parseColor(settings.backgroundColor))
        image.recycle()
        val flags = when (settings.wallpaperTarget) {
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
        /** One update at a time (the worker and the window may ask at the same moment). */
        private val lock = Mutex()
    }
}
