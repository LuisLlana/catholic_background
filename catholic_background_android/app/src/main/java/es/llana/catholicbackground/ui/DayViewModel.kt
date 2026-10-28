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
import java.time.LocalDate

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
    /** Day of the image this application last set as wallpaper, if any. */
    var lastSetDay by mutableStateOf(parseDay(settings.lastSetDay)); private set
    /** The wallpaper set by this application is kept up to date with the image of the day. */
    var followWallpaper by mutableStateOf(settings.followTarget.isNotEmpty()); private set

    fun stopFollowing() {
        settings.followTarget = ""
        followWallpaper = false
        Scheduler.scheduleWallpaper(getApplication())
    }
    var languages by mutableStateOf(ServerClient.FALLBACK_LANGUAGES); private set

    /** Short messages for the snackbar. */
    val messages = MutableSharedFlow<String>(extraBufferCapacity = 4)

    // Every property must be declared before init {}, which already calls load()
    /** The artwork shown is not the one of the current turn (it came with "Next image"). */
    var alternative by mutableStateOf(false); private set

    private var loadingJob: Job? = null
    /** Day the application was showing as "today": on another day it goes to the new today. */
    private var openedOn = LocalDate.now()

    init {
        load(LocalDate.now())
        loadLanguages()
    }

    /** When the application is shown again on another day (for example from the notification): today. */
    fun resumed() {
        // A new image may have come out while the application was closed
        if (settings.followTarget.isNotEmpty() && !busy) {
            viewModelScope.launch {
                if (updater.keepUpToDate()) lastSetDay = parseDay(settings.lastSetDay)
                followWallpaper = settings.followTarget.isNotEmpty()
            }
        }
        val today = LocalDate.now()
        if (today != openedOn) {
            openedOn = today
            load(today)
        }
    }

    /** Another artwork of the same day: the one after the artwork shown (back to the first after the last). */
    fun nextImage() {
        val current = artwork ?: return
        if (current.count > 1) load(day, after = current.id)
    }

    fun load(newDay: LocalDate, after: Long? = null) {
        loadingJob?.cancel()
        alternative = after != null
        day = newDay
        loading = true
        error = null
        artwork = null
        image = null
        loadingJob = viewModelScope.launch {
            try {
                // The artwork alone: its data are shown below it
                val url = ServerClient.requestUrl(settings.serverUrl, newDay, settings.languageCode(), label = false, next = after)
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

    /** The day shown becomes the wallpaper of target ("home", "lock" or "both"). */
    fun setWallpaper(target: String) {
        if (busy) return
        busy = true
        val shown = day
        viewModelScope.launch {
            val (ok, message) = updater.set(shown, target)
            messages.emit(message)
            lastSetDay = parseDay(settings.lastSetDay)
            if (ok) {
                followWallpaper = true
                Scheduler.scheduleWallpaper(getApplication())
            }
            busy = false
        }
    }

    private fun parseDay(text: String): LocalDate? = try {
        if (text.isEmpty()) null else LocalDate.parse(text)
    } catch (e: java.time.format.DateTimeParseException) {
        null
    }

    /** After the settings changed: texts in the new language, new server, new notification time. */
    fun settingsChanged(reloadDay: Boolean) {
        Scheduler.scheduleNotification(getApplication())
        if (reloadDay) {
            load(day)
            loadLanguages()
        }
    }

    private fun loadLanguages() {
        viewModelScope.launch { languages = ServerClient.fetchLanguages(settings.serverUrl) }
    }

}
