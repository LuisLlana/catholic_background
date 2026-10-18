// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later
package es.llana.catholicbackground.data

import android.content.Context
import androidx.core.content.edit
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

    /** Day of the image this application last set as wallpaper (ISO date); "" = none. */
    var lastSetDay: String
        get() = string("last_set_day", "")
        set(value) = setString("last_set_day", value)

    /** Date (ISO) on which that wallpaper was set, and SHA-1 of its image. */
    var lastSetOn: String
        get() = string("last_set_on", "")
        set(value) = setString("last_set_on", value)
    var lastSetHash: String
        get() = string("last_set_hash", "")
        set(value) = setString("last_set_hash", value)

    /**
     * Where the wallpaper set by this application is kept up to date with the image of the
     * day ("home", "lock" or "both"); "" = it is not (never set, turned off, or the user put
     * another wallpaper).
     */
    var followTarget: String
        get() = string("follow_target", "")
        set(value) = setString("follow_target", value)

    /** Ids the system gave to the wallpapers this application set (to notice another one). */
    var homeWallpaperId: Int
        get() = prefs.getInt("home_wallpaper_id", -1)
        set(value) = prefs.edit { putInt("home_wallpaper_id", value) }
    var lockWallpaperId: Int
        get() = prefs.getInt("lock_wallpaper_id", -1)
        set(value) = prefs.edit { putInt("lock_wallpaper_id", value) }

    /** Day (ISO date) of the last notification the alarm tried to show; "" = never. */
    var lastAttemptDay: String
        get() = string("last_attempt_day", "")
        set(value) = setString("last_attempt_day", value)

    /** Day (ISO date) of the last notification shown (or of a day without image); "" = never. */
    var lastNotifiedDay: String
        get() = string("last_notified_day", "")
        set(value) = setString("last_notified_day", value)

    /** "blur", "average" or "color". */
    var background: String
        get() = string("background", "blur")
        set(value) = setString("background", value)

    var backgroundColor: String
        get() = string("background_color", "#000000")
        set(value) = setString("background_color", value)

    fun languageCode(): String = language.ifEmpty { Locale.getDefault().toLanguageTag().lowercase() }

    companion object {
        /** Where an image can be set as wallpaper. */
        val TARGETS = listOf("home", "lock", "both")
    }
}
