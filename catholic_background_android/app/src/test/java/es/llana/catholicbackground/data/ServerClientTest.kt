// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later
package es.llana.catholicbackground.data

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test
import java.time.LocalDate
import java.time.ZoneId
import java.util.Base64

class ServerClientTest {
    private val madrid = ZoneId.of("Europe/Madrid")

    @Test
    fun requestUrlHasTheLocalMidnightLanguageAndLabel() {
        val url = ServerClient.requestUrl("https://simba.fdi.ucm.es/background", LocalDate.of(2026, 3, 19), "es-es", true, madrid)
        assertEquals("https://simba.fdi.ucm.es/background?ts=1773874800&lang=es-es", url)
        val noLabel = ServerClient.requestUrl("https://simba.fdi.ucm.es/background", LocalDate.of(2026, 3, 19), "en", false, madrid)
        assertEquals("https://simba.fdi.ucm.es/background?ts=1773874800&lang=en&caption=0", noLabel)
    }

    @Test
    fun requestUrlKeepsOtherParametersAndReplacesOurs() {
        val url = ServerClient.requestUrl("http://host:8000/bg?key=1&ts=5&lang=fr", LocalDate.of(2026, 3, 19), "", true, madrid)
        assertEquals("http://host:8000/bg?key=1&ts=1773874800", url)
    }

    @Test
    fun onlyHttpAddressesAreAccepted() {
        for (bad in listOf("file:///etc/passwd", "ftp://host/x", "not a url", "")) {
            try {
                ServerClient.requestUrl(bad, LocalDate.of(2026, 3, 19), "es", true, madrid)
                fail("accepted $bad")
            } catch (e: ServerException) {
                assertEquals(Problem.INVALID_URL, e.problem)
            }
        }
    }

    @Test
    fun languagesUrl() {
        assertEquals("https://simba.fdi.ucm.es/background/languages", ServerClient.languagesUrl("https://simba.fdi.ucm.es/background/"))
    }

    @Test
    fun parsesAnArtwork() {
        val image = byteArrayOf(1, 2, 3)
        val body = """{"image": "${Base64.getEncoder().encodeToString(image)}", "title": "La Anunciación", "author": "Fra Angelico",
            "date": "c. 1426", "description": null, "reason": "Tiempo ordinario", "license": "Dominio público",
            "source": "https://example.com", "edit_url": "https://x/admin/1/", "language": "es",
            "extra": {"Museo": "Prado", "Vacío": ""}, "id": 42, "position": 2, "count": 3}"""
        val artwork = ServerClient.parseArtwork(body)
        assertEquals(listOf(1, 2, 3), artwork.bytes.map { it.toInt() })
        assertEquals("7037807198c22a7d2b0807371d763779a84fdfcf", artwork.hash)   // SHA-1 of 01 02 03
        assertEquals("La Anunciación", artwork.title)
        assertEquals("c. 1426", artwork.year)
        assertEquals("", artwork.description)
        assertEquals("Tiempo ordinario", artwork.reason)
        assertEquals(listOf("Museo" to "Prado"), artwork.extra)
        assertEquals("https://x/admin/1/", artwork.editUrl)
        assertEquals(Triple(42L, 2, 3), Triple(artwork.id, artwork.position, artwork.count))
    }

    @Test
    fun requestUrlWithNext() {
        val url = ServerClient.requestUrl("https://simba.fdi.ucm.es/background?next=7", LocalDate.of(2026, 3, 19), "es", false, madrid, next = 42)
        assertEquals("https://simba.fdi.ucm.es/background?ts=1773874800&lang=es&caption=0&next=42", url)
    }

    @Test
    fun invalidAnswers() {
        for (body in listOf("<html>", "{}", """{"image": "%%%"}""")) {
            try {
                ServerClient.parseArtwork(body)
                fail("accepted $body")
            } catch (e: ServerException) {
                assertEquals(Problem.INVALID_ANSWER, e.problem)
            }
        }
    }

    @Test
    fun languagesWithFallback() {
        assertEquals(listOf(ContentLanguage("es", "Español"), ContentLanguage("fr", "Français")),
            ServerClient.parseLanguages("""{"default": "es", "languages": [{"code": "es", "name": "Español"}, {"code": "fr", "name": "Français"}]}"""))
        assertEquals(ServerClient.FALLBACK_LANGUAGES, ServerClient.parseLanguages("not json"))
    }

    @Test
    fun onlyWebLinksAreOpened() {
        assertTrue(ServerClient.isWebLink("https://example.com"))
        assertTrue(ServerClient.isWebLink("HTTP://example.com"))
        assertFalse(ServerClient.isWebLink("javascript:alert(1)"))
        assertFalse(ServerClient.isWebLink("file:///sdcard/x"))
    }
}
