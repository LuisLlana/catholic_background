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
import androidx.compose.ui.window.DialogProperties
import es.llana.catholicbackground.R

/** What can be done with an image, with its text: set it somewhere, or only see it. */
val IMAGE_CHOICES = listOf(
    "home" to R.string.target_home,
    "lock" to R.string.target_lock,
    "both" to R.string.target_both,
    "none" to R.string.target_none,
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
 * What to do with the image of a day: wallpaper of the home screen, of the lock screen, of
 * both, or only see it. Nothing is preselected: the user chooses explicitly.
 * required: the daily question, which cannot be dismissed without answering.
 */
@Composable
fun ImageChoiceDialog(dayText: String, required: Boolean, onDismiss: () -> Unit = {}, onChoice: (String) -> Unit) {
    var selected by rememberSaveable { mutableStateOf<String?>(null) }
    AlertDialog(
        onDismissRequest = { if (!required) onDismiss() },
        properties = DialogProperties(dismissOnBackPress = !required, dismissOnClickOutside = !required),
        title = { Text(stringResource(R.string.image_question_title)) },
        text = {
            Column {
                Text(stringResource(R.string.image_question_text, dayText), Modifier.padding(bottom = 12.dp))
                RadioList(IMAGE_CHOICES, selected) { selected = it }
            }
        },
        confirmButton = {
            TextButton(onClick = { selected?.let(onChoice) }, enabled = selected != null) {
                Text(stringResource(android.R.string.ok))
            }
        },
        dismissButton = if (required) null else {
            { TextButton(onClick = onDismiss) { Text(stringResource(android.R.string.cancel)) } }
        },
    )
}
