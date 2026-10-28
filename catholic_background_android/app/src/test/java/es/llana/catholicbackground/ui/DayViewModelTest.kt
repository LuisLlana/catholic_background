// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later
package es.llana.catholicbackground.ui

import android.app.Application
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.annotation.Config
import java.time.LocalDate

/** The main screen starts: the view model is created (its init already loads today). Version 0.6.4 crashed here. */
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35], application = Application::class)
class DayViewModelTest {
    @Test
    fun startsWithToday() {
        val model = DayViewModel(RuntimeEnvironment.getApplication())
        assertEquals(LocalDate.now(), model.day)
        assertFalse(model.alternative)
    }
}
