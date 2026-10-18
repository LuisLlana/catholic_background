// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later
package es.llana.catholicbackground.wallpaper

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.LocalDate

class KeepUpToDateTest {
    private val today = LocalDate.of(2026, 10, 18)
    private fun needs(lastSetOn: String, lastSetDay: String, lastHash: String, hash: String) =
        WallpaperUpdater.needsUpdate(today, lastSetOn, lastSetDay, lastHash, hash)

    @Test fun sameImageOfTodayIsKept() = assertFalse(needs("2026-10-18", "2026-10-18", "a", "a"))
    @Test fun newImageOfTodayReplacesIt() = assertTrue(needs("2026-10-18", "2026-10-18", "a", "b"))
    @Test fun anotherDayChosenTodayStays() = assertFalse(needs("2026-10-18", "2026-12-25", "x", "b"))
    @Test fun nextDayAlwaysReplacesIt() = assertTrue(needs("2026-10-17", "2026-10-17", "a", "a"))
    @Test fun dayChosenYesterdayIsReplaced() = assertTrue(needs("2026-10-17", "2026-12-25", "x", "b"))
}
