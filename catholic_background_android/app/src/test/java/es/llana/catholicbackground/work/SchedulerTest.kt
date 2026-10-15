// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later
package es.llana.catholicbackground.work

import org.junit.Assert.assertEquals
import org.junit.Test
import java.time.LocalDateTime

class SchedulerTest {
    private val nine = 9 * 60
    private fun at(day: Int, hour: Int, minute: Int = 0) = LocalDateTime.of(2026, 10, day, hour, minute)

    @Test fun beforeTheTimeIsToday() =
        assertEquals(at(15, 9), Scheduler.nextTime(at(15, 8, 30), nine, "2026-10-14"))

    @Test fun afterTheTimeAlreadyTriedIsTomorrow() =
        assertEquals(at(16, 9), Scheduler.nextTime(at(15, 9), nine, "2026-10-15"))

    @Test fun missedTodayIsInAMinute() =
        assertEquals(at(15, 12, 1), Scheduler.nextTime(at(15, 12), nine, "2026-10-14"))

    @Test fun justInstalledAfterTheTimeIsTomorrow() =
        assertEquals(at(16, 9), Scheduler.nextTime(at(15, 16), nine, ""))
}
