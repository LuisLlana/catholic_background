// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later
package es.llana.catholicbackground.ui

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import androidx.core.content.ContextCompat
import java.time.format.DateTimeFormatter
import java.time.format.FormatStyle

class MainActivity : ComponentActivity() {
    private val model: DayViewModel by viewModels()

    private val askNotifications = registerForActivityResult(ActivityResultContracts.RequestPermission()) {}

    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)
        // The very first time, the permission is asked after the question about the image
        if (model.settings.answeredDay.isNotEmpty()) askForNotifications()
        setContent {
            val dark = isSystemInDarkTheme()
            val context = LocalContext.current
            val colors = when {
                Build.VERSION.SDK_INT >= 31 -> if (dark) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
                dark -> darkColorScheme()
                else -> lightColorScheme()
            }
            MaterialTheme(colorScheme = colors) {
                var settingsOpen by rememberSaveable { mutableStateOf(false) }
                if (settingsOpen) {
                    BackHandler { settingsOpen = false }
                    SettingsScreen(model, onBack = { settingsOpen = false })
                } else {
                    DayScreen(model, onSettings = { settingsOpen = true })
                }
                // Once a day: what to do with the image of today, asked explicitly
                if (model.questionVisible) {
                    val first = model.settings.answeredDay.isEmpty()
                    ImageChoiceDialog(
                        dayText = model.day.format(DateTimeFormatter.ofLocalizedDate(FormatStyle.LONG)),
                        required = true,
                    ) { choice ->
                        model.answerToday(choice)
                        if (first) askForNotifications()
                    }
                }
            }
        }
    }

    /** Android 13+: the daily notification needs permission. */
    private fun askForNotifications() {
        if (Build.VERSION.SDK_INT >= 33 && model.settings.notifications &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            askNotifications.launch(Manifest.permission.POST_NOTIFICATIONS)
        }
    }

    override fun onResume() {
        super.onResume()
        model.resumed()
    }
}
