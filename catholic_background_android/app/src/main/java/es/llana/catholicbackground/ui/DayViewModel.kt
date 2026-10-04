// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later
package es.llana.catholicbackground.ui

import android.app.Application
import android.graphics.BitmapFactory
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import es.llana.catholicbackground.R
import es.llana.catholicbackground.data.Artwork
import es.llana.catholicbackground.data.ContentLanguage
import es.llana.catholicbackground.data.ServerClient
import es.llana.catholicbackground.data.ServerException
import es.llana.catholicbackground.data.Settings
import es.llana.catholicbackground.wallpaper.WallpaperUpdater
import es.llana.catholicbackground.work.Scheduler
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.text.DateFormat
import java.time.LocalDate
import java.util.Date

/** State of the main screen: the day shown, its artwork and the actions on the wallpaper. */
class DayViewModel(application: Application) : AndroidViewModel(application) {
    val settings = Settings(application)
    private val updater = WallpaperUpdater(application)

    var day by mutableStateOf(LocalDate.now()); private set
    var loading by mutableStateOf(false); private set
    var error by mutableStateOf<String?>(null); private set
    var artwork by mutableStateOf<Artwork?>(null); private set
    var image by mutableStateOf<ImageBitmap?>(null); private set
    var busy by mutableStateOf(false); private set
    var wallpaperDay by mutableStateOf(settings.wallpaperDay()); private set
    var status by mutableStateOf(""); private set
    var languages by mutableStateOf(ServerClient.FALLBACK_LANGUAGES); private set

    /** Short messages for the snackbar. */
    val messages = MutableSharedFlow<String>(extraBufferCapacity = 4)

    private var loadingJob: Job? = null

    init {
        updateStatus()
        load(LocalDate.now())
        loadLanguages()
    }

    fun load(newDay: LocalDate) {
        loadingJob?.cancel()
        day = newDay
        loading = true
        error = null
        artwork = null
        image = null
        loadingJob = viewModelScope.launch {
            try {
                // The artwork alone: its data are shown below it
                val url = ServerClient.requestUrl(settings.serverUrl, newDay, settings.languageCode(), label = false)
                val result = ServerClient.fetchArtwork(url)
                val bitmap = withContext(Dispatchers.Default) {
                    BitmapFactory.decodeByteArray(result.bytes, 0, result.bytes.size)?.asImageBitmap()
                }
                if (bitmap == null) {
                    error = getApplication<Application>().getString(R.string.problem_invalid_answer)
                } else {
                    artwork = result
                    image = bitmap
                }
            } catch (e: ServerException) {
                error = problemText(getApplication(), e)
            } finally {
                loading = false
            }
        }
    }

    fun shift(days: Long) = load(day.plusDays(days))

    fun today() = load(LocalDate.now())

    /** The day shown becomes the wallpaper until the next automatic check (today: back to normal). */
    fun useAsWallpaper() = changeWallpaper {
        settings.showDate = if (day == LocalDate.now()) "" else day.toString()
    }

    fun refreshWallpaper() = changeWallpaper {}

    private fun changeWallpaper(before: () -> Unit) {
        if (busy) return
        busy = true
        before()
        wallpaperDay = settings.wallpaperDay()
        viewModelScope.launch {
            val (_, message) = updater.update(force = true)
            messages.emit(message)
            busy = false
            wallpaperDay = settings.wallpaperDay()
            updateStatus()
        }
    }

    /** After the settings changed: texts in the new language, new server, new schedules. */
    fun settingsChanged(reloadDay: Boolean, rescheduleUpdates: Boolean) {
        Scheduler.scheduleUpdates(getApplication(), replace = rescheduleUpdates)
        Scheduler.scheduleNotification(getApplication())
        if (reloadDay) {
            load(day)
            loadLanguages()
        }
        updateStatus()
    }

    private fun loadLanguages() {
        viewModelScope.launch { languages = ServerClient.fetchLanguages(settings.serverUrl) }
    }

    fun updateStatus() {
        val app = getApplication<Application>()
        status = if (settings.lastCheck == 0L) app.getString(R.string.never_checked)
        else app.getString(R.string.last_check,
            DateFormat.getTimeInstance(DateFormat.SHORT).format(Date(settings.lastCheck)), settings.lastResult)
    }
}
