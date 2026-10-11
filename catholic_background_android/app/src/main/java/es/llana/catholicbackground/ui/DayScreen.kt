// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later
package es.llana.catholicbackground.ui

import android.content.Intent
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DatePicker
import androidx.compose.material3.DatePickerDialog
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.rememberDatePickerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp
import androidx.core.net.toUri
import es.llana.catholicbackground.R
import es.llana.catholicbackground.data.ServerClient
import es.llana.catholicbackground.data.Settings
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter
import java.time.format.FormatStyle

private val ReasonColor = Color(0xFFB07A14)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DayScreen(model: DayViewModel, onSettings: () -> Unit) {
    val context = LocalContext.current
    val snackbar = remember { SnackbarHostState() }
    var choosingDay by remember { mutableStateOf(false) }
    var choosingTarget by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) { model.messages.collect { snackbar.showSnackbar(it) } }

    fun open(url: String) {
        if (ServerClient.isWebLink(url)) context.startActivity(Intent(Intent.ACTION_VIEW, url.toUri()))
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.app_name)) },
                actions = { TextButton(onClick = onSettings) { Text(stringResource(R.string.settings)) } },
            )
        },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { padding ->
        Column(
            Modifier.padding(padding).fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            // ---- choice of the day
            Row(verticalAlignment = Alignment.CenterVertically) {
                OutlinedButton(onClick = { model.shift(-1) }) { Text("\u25C0") }
                TextButton(onClick = { choosingDay = true }, modifier = Modifier.weight(1f)) {
                    Text(model.day.format(DateTimeFormatter.ofLocalizedDate(FormatStyle.FULL)))
                }
                OutlinedButton(onClick = { model.shift(1) }) { Text("\u25B6") }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = { model.today() }, enabled = model.day != LocalDate.now()) {
                    Text(stringResource(R.string.today))
                }
                Spacer(Modifier.weight(1f))
                Button(onClick = { choosingTarget = true }, enabled = !model.busy && model.artwork != null) {
                    Text(stringResource(R.string.use_as_wallpaper))
                }
            }
            if (model.day == model.lastSetDay) {
                Text(stringResource(R.string.set_as_wallpaper_note), style = MaterialTheme.typography.bodySmall)
            }

            // ---- the image
            Box(
                Modifier.fillMaxWidth().heightIn(min = 200.dp).clip(RoundedCornerShape(12.dp)),
                contentAlignment = Alignment.Center,
            ) {
                val image = model.image
                when {
                    model.loading -> CircularProgressIndicator(Modifier.padding(48.dp))
                    model.error != null -> Text(model.error!!, Modifier.padding(32.dp), style = MaterialTheme.typography.bodyLarge)
                    image != null -> Image(
                        bitmap = image,
                        contentDescription = model.artwork?.title,
                        contentScale = ContentScale.Fit,
                        modifier = Modifier.fillMaxWidth().heightIn(max = 560.dp),
                    )
                }
            }

            // ---- its data
            model.artwork?.let { artwork ->
                SelectionContainer {
                    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        if (artwork.reason.isNotEmpty()) {
                            Text(artwork.reason, color = ReasonColor, fontWeight = FontWeight.Bold)
                        }
                        Text(artwork.title.ifEmpty { stringResource(R.string.untitled) }, style = MaterialTheme.typography.headlineSmall)
                        val authorYear = listOf(artwork.author, artwork.year).filter { it.isNotEmpty() }.joinToString(", ")
                        if (authorYear.isNotEmpty()) Text(authorYear, style = MaterialTheme.typography.titleMedium)
                        if (artwork.description.isNotEmpty()) {
                            Text(artwork.description, Modifier.padding(top = 8.dp), style = MaterialTheme.typography.bodyLarge)
                        }
                        val rows = artwork.extra + listOfNotNull(
                            artwork.license.takeIf { it.isNotEmpty() }?.let { stringResource(R.string.license) to it })
                        Column(Modifier.padding(top = 8.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                            rows.forEach { (name, value) ->
                                Row {
                                    Text(name, Modifier.width(110.dp), fontWeight = FontWeight.Bold)
                                    Text(value)
                                }
                            }
                            if (artwork.source.isNotEmpty()) {
                                Row {
                                    Text(stringResource(R.string.source), Modifier.width(110.dp), fontWeight = FontWeight.Bold)
                                    if (ServerClient.isWebLink(artwork.source)) {
                                        TextButton(onClick = { open(artwork.source) }, contentPadding = androidx.compose.foundation.layout.PaddingValues(0.dp)) {
                                            Text(artwork.source, textDecoration = TextDecoration.Underline)
                                        }
                                    } else {
                                        Text(artwork.source)
                                    }
                                }
                            }
                        }
                    }
                }
                FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    if (artwork.editUrl.isNotEmpty()) {
                        OutlinedButton(onClick = { open(artwork.editUrl) }) { Text(stringResource(R.string.edit_image)) }
                    }
                }
            }
            Spacer(Modifier.padding(bottom = 8.dp))
        }
    }

    if (choosingTarget) {
        ImageChoiceDialog(
            dayText = model.day.format(DateTimeFormatter.ofLocalizedDate(FormatStyle.LONG)),
            required = false,
            onDismiss = { choosingTarget = false },
        ) { choice ->
            choosingTarget = false
            if (choice in Settings.TARGETS) model.setWallpaper(choice)
        }
    }

    if (choosingDay) {
        val state = rememberDatePickerState(initialSelectedDateMillis = model.day.toEpochDay() * 86_400_000L)
        DatePickerDialog(
            onDismissRequest = { choosingDay = false },
            confirmButton = {
                TextButton(onClick = {
                    state.selectedDateMillis?.let { model.load(Instant.ofEpochMilli(it).atZone(ZoneOffset.UTC).toLocalDate()) }
                    choosingDay = false
                }) { Text(stringResource(android.R.string.ok)) }
            },
            dismissButton = { TextButton(onClick = { choosingDay = false }) { Text(stringResource(android.R.string.cancel)) } },
        ) {
            DatePicker(state)
        }
    }
}
