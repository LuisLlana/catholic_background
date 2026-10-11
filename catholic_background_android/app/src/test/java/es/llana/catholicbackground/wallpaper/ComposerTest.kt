// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later
package es.llana.catholicbackground.wallpaper

import org.junit.Assert.assertEquals
import org.junit.Test

class ComposerTest {
    @Test
    fun aWideArtworkFillsTheWidthOfAPhone() {
        // 1600×1000 on a 1080×2400 screen: full width, centred vertically
        assertEquals(Composer.Box(0, 862, 1080, 675), Composer.fit(1600, 1000, 1080, 2400))
    }

    @Test
    fun aTallArtworkFillsTheHeight() {
        // 900×3000 on 1080×2400: full height, centred horizontally
        assertEquals(Composer.Box(180, 0, 720, 2400), Composer.fit(900, 3000, 1080, 2400))
    }
}
