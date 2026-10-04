// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later
package es.llana.catholicbackground.data

import android.content.Context
import androidx.core.content.edit
import java.time.LocalDate
import java.time.format.DateTimeParseException
import java.util.Locale

/** Settings and state of the application. */
class Settings(context: Context) {
    private val prefs = context.applicationContext.getSharedPreferences("settings", Context.MODE_PRIVATE)

    private fun string(key: String, default: String) = prefs.getString(key, default) ?: default
    private fun setString(key: String, value: String) = prefs.edit { putString(key, value) }

    var serverUrl: String
        get() = string("server_url", ServerClient.DEFAULT_SERVER)
        set(value) = setString("server_url", value)

    /** Language of the texts ("" = that of the system). */
    var language: String
        get() = string("language", "")
        set(value) = setString("language", value)

    var showLabel: Boolean
        get() = prefs.getBoolean("show_label", true)
        set(value) = prefs.edit { putBoolean("show_label", value) }

    var notifications: Boolean
        get() = prefs.getBoolean("notifications", true)
        set(value) = prefs.edit { putBoolean("notifications", value) }

    /** Time of the daily notification, in minutes after midnight. */
    var notificationMinutes: Int
        get() = prefs.getInt("notification_minutes", 9 * 60)
        set(value) = prefs.edit { putInt("notification_minutes", value.coerceIn(0, 24 * 60 - 1)) }

    var autoWallpaper: Boolean
        get() = prefs.getBoolean("auto_wallpaper", true)
        set(value) = prefs.edit { putBoolean("auto_wallpaper", value) }

    /** "both", "home" or "lock". */
    var wallpaperTarget: String
        get() = string("wallpaper_target", "both")
        set(value) = setString("wallpaper_target", value)

    /** "blur", "average" or "color". */
    var background: String
        get() = string("background", "blur")
        set(value) = setString("background", value)

    var backgroundColor: String
        get() = string("background_color", "#000000")
        set(value) = setString("background_color", value)

    var checkIntervalMinutes: Int
        get() = prefs.getInt("check_interval", 60)
        set(value) = prefs.edit { putInt("check_interval", value.coerceIn(MIN_INTERVAL, 24 * 60)) }

    /** Day used as wallpaper (ISO date) until the next automatic check; "" = today. */
    var showDate: String
        get() = string("show_date", "")
        set(value) = setString("show_date", value)

    var imageHash: String
        get() = string("image_hash", "")
        set(value) = setString("image_hash", value)

    var lastCheck: Long
        get() = prefs.getLong("last_check", 0)
        set(value) = prefs.edit { putLong("last_check", value) }

    var lastResult: String
        get() = string("last_result", "")
        set(value) = setString("last_result", value)

    fun languageCode(): String = language.ifEmpty { Locale.getDefault().toLanguageTag().lowercase() }

    fun wallpaperDay(): LocalDate = try {
        if (showDate.isEmpty()) LocalDate.now() else LocalDate.parse(showDate)
    } catch (e: DateTimeParseException) {
        LocalDate.now()
    }

    fun wallpaperUrl(): String = ServerClient.requestUrl(serverUrl, wallpaperDay(), languageCode(), showLabel)

    companion object {
        /** WorkManager does not run periodic work more often than every 15 minutes. */
        const val MIN_INTERVAL = 15
    }
}
