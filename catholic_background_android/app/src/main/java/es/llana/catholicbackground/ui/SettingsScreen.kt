// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later
package es.llana.catholicbackground.ui

import android.widget.Toast
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.ExposedDropdownMenuAnchorType
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TimePicker
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.rememberTimePickerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalResources
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import es.llana.catholicbackground.BuildConfig
import es.llana.catholicbackground.R
import es.llana.catholicbackground.data.ServerClient
import es.llana.catholicbackground.data.ServerException
import kotlinx.coroutines.launch
import java.time.LocalDate
import java.time.LocalTime
import java.time.format.DateTimeFormatter
import java.time.format.FormatStyle

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(model: DayViewModel, onBack: () -> Unit) {
    val settings = model.settings
    val context = LocalContext.current
    // Configuration-aware: texts follow a change of the language of the device
    val resources = LocalResources.current
    val locale = LocalConfiguration.current.locales[0]
    val scope = rememberCoroutineScope()
    var url by remember { mutableStateOf(settings.serverUrl) }
    var language by remember { mutableStateOf(settings.language) }
    var label by remember { mutableStateOf(settings.showLabel) }
    var notifications by remember { mutableStateOf(settings.notifications) }
    var minutes by remember { mutableStateOf(settings.notificationMinutes) }
    var background by remember { mutableStateOf(settings.background) }
    var color by remember { mutableStateOf(settings.backgroundColor) }
    var choosingTime by remember { mutableStateOf(false) }
    fun toast(text: String) = Toast.makeText(context, text, Toast.LENGTH_LONG).show()

    Scaffold(topBar = {
        TopAppBar(
            title = { Text(stringResource(R.string.settings)) },
            navigationIcon = { TextButton(onClick = onBack) { Text("\u2190") } },
        )
    }) { padding ->
        Column(
            Modifier.padding(padding).fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            // ---- server
            OutlinedTextField(url, { url = it }, Modifier.fillMaxWidth(), label = { Text(stringResource(R.string.server_url)) }, singleLine = true)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = {
                    try {
                        ServerClient.validate(url)
                        val changed = url.trim() != settings.serverUrl
                        settings.serverUrl = url.trim()
                        toast(resources.getString(R.string.server_saved))
                        model.settingsChanged(reloadDay = changed)
                    } catch (e: ServerException) {
                        toast(problemText(context, e))
                    }
                }) { Text(stringResource(R.string.save)) }
                OutlinedButton(onClick = {
                    scope.launch {
                        try {
                            val a = ServerClient.fetchArtwork(ServerClient.requestUrl(url, LocalDate.now(), settings.languageCode(), label = false))
                            toast(resources.getString(R.string.connection_ok, a.title.ifEmpty { "—" }))
                        } catch (e: ServerException) {
                            toast(problemText(context, e))
                        }
                    }
                }) { Text(stringResource(R.string.test)) }
                TextButton(onClick = { url = ServerClient.DEFAULT_SERVER }) { Text(stringResource(R.string.default_server)) }
            }
            HorizontalDivider()

            // ---- texts
            var expanded by remember { mutableStateOf(false) }
            val system = locale.getDisplayLanguage(locale).replaceFirstChar { it.titlecase(locale) }
            val options = listOf("" to resources.getString(R.string.system_language, system)) + model.languages.map { it.code to it.name }
            ExposedDropdownMenuBox(expanded, { expanded = it }) {
                OutlinedTextField(
                    value = options.firstOrNull { it.first == language }?.second ?: language,
                    onValueChange = {}, readOnly = true,
                    label = { Text(stringResource(R.string.language)) },
                    trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded) },
                    modifier = Modifier.menuAnchor(ExposedDropdownMenuAnchorType.PrimaryNotEditable).fillMaxWidth(),
                )
                ExposedDropdownMenu(expanded, { expanded = false }) {
                    options.forEach { (code, name) ->
                        DropdownMenuItem(text = { Text(name) }, onClick = {
                            expanded = false
                            if (code != settings.language) {
                                language = code
                                settings.language = code
                                model.settingsChanged(reloadDay = true)
                            }
                        })
                    }
                }
            }
            SwitchRow(stringResource(R.string.label_title), stringResource(R.string.label_summary), label) {
                label = it
                settings.showLabel = it
            }
            HorizontalDivider()

            // ---- notification
            SwitchRow(stringResource(R.string.notifications_title), stringResource(R.string.notifications_summary), notifications) {
                notifications = it
                settings.notifications = it
                model.settingsChanged(reloadDay = false)
            }
            if (notifications) {
                val time = LocalTime.of(minutes / 60, minutes % 60)
                OutlinedButton(onClick = { choosingTime = true }) {
                    Text(stringResource(R.string.notification_time, time.format(DateTimeFormatter.ofLocalizedTime(FormatStyle.SHORT))))
                }
            }
            HorizontalDivider()

            // ---- wallpaper
            Text(stringResource(R.string.around_image), style = MaterialTheme.typography.titleSmall)
            Choice(listOf("blur" to R.string.blur, "average" to R.string.average, "color" to R.string.color), background) {
                background = it
                settings.background = it
            }
            if (background == "color") {
                OutlinedTextField(color, {
                    color = it
                    if (Regex("#[0-9a-fA-F]{6}").matches(it)) settings.backgroundColor = it
                }, label = { Text(stringResource(R.string.color_hex)) }, singleLine = true)
            }
            Text(stringResource(R.string.apply_note), style = MaterialTheme.typography.bodySmall)
            HorizontalDivider()
            Text(stringResource(R.string.about, BuildConfig.VERSION_NAME), style = MaterialTheme.typography.bodySmall)
        }
    }

    if (choosingTime) {
        val state = rememberTimePickerState(minutes / 60, minutes % 60)
        AlertDialog(
            onDismissRequest = { choosingTime = false },
            confirmButton = {
                TextButton(onClick = {
                    minutes = state.hour * 60 + state.minute
                    settings.notificationMinutes = minutes
                    model.settingsChanged(reloadDay = false)
                    choosingTime = false
                }) { Text(stringResource(android.R.string.ok)) }
            },
            dismissButton = { TextButton(onClick = { choosingTime = false }) { Text(stringResource(android.R.string.cancel)) } },
            text = { TimePicker(state) },
        )
    }
}

@Composable
private fun SwitchRow(title: String, summary: String, checked: Boolean, onChange: (Boolean) -> Unit) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Column(Modifier.weight(1f)) {
            Text(title, style = MaterialTheme.typography.titleMedium)
            Text(summary, style = MaterialTheme.typography.bodySmall)
        }
        Switch(checked, onChange)
    }
}

@Composable
private fun <T> Choice(options: List<Pair<T, Int>>, selected: T, onSelect: (T) -> Unit) {
    Column {
        options.forEach { (value, text) ->
            Row(
                Modifier.fillMaxWidth().selectable(selected = value == selected, onClick = { onSelect(value) }),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                RadioButton(selected = value == selected, onClick = { onSelect(value) })
                Text(stringResource(text))
            }
        }
    }
}
