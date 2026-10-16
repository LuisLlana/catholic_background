// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later
package es.llana.catholicbackground.ui

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.selectableGroup
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.unit.dp
import es.llana.catholicbackground.R

/** Where an image can be set as wallpaper, with its text. */
val WALLPAPER_TARGETS = listOf(
    "home" to R.string.target_home,
    "lock" to R.string.target_lock,
    "both" to R.string.target_both,
)

@Composable
fun RadioList(options: List<Pair<String, Int>>, selected: String?, onSelect: (String) -> Unit) {
    Column(Modifier.selectableGroup()) {
        options.forEach { (value, text) ->
            Row(
                Modifier.fillMaxWidth()
                    .selectable(selected = value == selected, onClick = { onSelect(value) }, role = Role.RadioButton)
                    .padding(vertical = 4.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                RadioButton(selected = value == selected, onClick = null)
                Text(stringResource(text), Modifier.padding(start = 12.dp))
            }
        }
    }
}

/**
 * "Use as wallpaper…": wallpaper of the home screen, of the lock screen or of both, for the
 * image of the day shown. Nothing is preselected: the user chooses explicitly.
 */
@Composable
fun WallpaperTargetDialog(dayText: String, onDismiss: () -> Unit, onChoice: (String) -> Unit) {
    var selected by rememberSaveable { mutableStateOf<String?>(null) }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.use_as_wallpaper)) },
        text = {
            Column {
                Text(stringResource(R.string.wallpaper_where_text, dayText), Modifier.padding(bottom = 12.dp))
                RadioList(WALLPAPER_TARGETS, selected) { selected = it }
            }
        },
        confirmButton = {
            TextButton(onClick = { selected?.let(onChoice) }, enabled = selected != null) {
                Text(stringResource(R.string.set_wallpaper))
            }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text(stringResource(android.R.string.cancel)) } },
    )
}
