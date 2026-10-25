// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later
package es.llana.catholicbackground.data

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONException
import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URI
import java.net.URL
import java.net.URLEncoder
import java.security.MessageDigest
import java.time.LocalDate
import java.time.ZoneId
import java.util.Base64

/** An artwork as sent by the server. */
class Artwork(
    val bytes: ByteArray,
    val hash: String,
    val title: String,
    val author: String,
    val year: String,
    val description: String,
    val reason: String,
    val license: String,
    val source: String,
    val editUrl: String,
    val language: String,
    val extra: List<Pair<String, String>>,
    /** Id of the artwork, and its place among the artworks of the day (0 with servers that do not send them). */
    val id: Long = 0,
    val position: Int = 0,
    val count: Int = 0,
)

data class ContentLanguage(val code: String, val name: String)

/** What went wrong, so that the interface can explain it in its language. */
enum class Problem { INVALID_URL, NO_IMAGE, CONNECTION, HTTP, INVALID_ANSWER }

class ServerException(val problem: Problem, message: String) : Exception(message)

/**
 * Access to the Catholic background of the day server:
 *   GET <url>?ts=<Unix timestamp of the local midnight of the day>&lang=<language>[&caption=0]
 *   -> {"image": "<base64>", "title", "author", "date", "description", "reason", "license",
 *       "source", "extra", "language", "edit_url", ...}
 *   GET <url>/languages -> {"default": "es", "languages": [{"code", "name"}, ...]}
 */
object ServerClient {
    const val DEFAULT_SERVER = "https://simba.fdi.ucm.es/background"

    private fun parseBase(base: String): URI {
        val uri = try {
            URI(base.trim())
        } catch (e: Exception) {
            null
        }
        if (uri == null || (uri.scheme != "http" && uri.scheme != "https") || uri.host.isNullOrEmpty()) {
            throw ServerException(Problem.INVALID_URL, "The URL must start with http:// or https://")
        }
        return uri
    }

    /** Throws ServerException if the URL is not valid. */
    fun validate(base: String) {
        parseBase(base)
    }

    /** base?ts=<local midnight of day>&lang=<language>[&caption=0], keeping other query parameters. */
    /** next: id of an artwork of the day, to get the one that follows it (another artwork of the same day). */
    fun requestUrl(base: String, day: LocalDate, language: String, label: Boolean, zone: ZoneId = ZoneId.systemDefault(),
                   next: Long? = null): String {
        val uri = parseBase(base)
        val parameters = (uri.rawQuery ?: "").split("&")
            .filter { it.isNotEmpty() && it.substringBefore("=") !in setOf("ts", "lang", "caption", "next") }
            .toMutableList()
        parameters += "ts=${day.atStartOfDay(zone).toEpochSecond()}"
        if (language.isNotEmpty()) parameters += "lang=${URLEncoder.encode(language, "UTF-8")}"
        if (!label) parameters += "caption=0"
        if (next != null) parameters += "next=$next"
        return URI(uri.scheme, uri.rawAuthority, uri.rawPath, null, null).toString() + "?" + parameters.joinToString("&")
    }

    /** <base>/languages */
    fun languagesUrl(base: String): String {
        val uri = parseBase(base)
        return URI(uri.scheme, uri.rawAuthority, (uri.rawPath ?: "").trimEnd('/') + "/languages", null, null).toString()
    }

    fun parseArtwork(body: String): Artwork {
        val json = try {
            JSONObject(body)
        } catch (e: JSONException) {
            throw ServerException(Problem.INVALID_ANSWER, "The server did not answer with JSON")
        }
        var encoded = json.optString("image", "")
        if (encoded.isEmpty()) throw ServerException(Problem.INVALID_ANSWER, "The answer has no image")
        if (encoded.startsWith("data:")) encoded = encoded.substringAfter(",")
        val bytes = try {
            Base64.getDecoder().decode(encoded)
        } catch (e: IllegalArgumentException) {
            throw ServerException(Problem.INVALID_ANSWER, "The image is not valid base64")
        }
        val extra = mutableListOf<Pair<String, String>>()
        json.optJSONObject("extra")?.let { obj ->
            for (key in obj.keys()) {
                val value = obj.optString(key, "").trim()
                if (value.isNotEmpty()) extra += key to value
            }
        }
        fun text(name: String) = if (json.isNull(name)) "" else json.optString(name, "").trim()
        return Artwork(
            bytes = bytes,
            hash = MessageDigest.getInstance("SHA-1").digest(bytes).joinToString("") { "%02x".format(it) },
            title = text("title"),
            author = text("author"),
            year = text("date"),
            description = text("description"),
            reason = text("reason"),
            license = text("license"),
            source = text("source"),
            editUrl = text("edit_url"),
            language = text("language"),
            extra = extra,
            id = json.optLong("id", 0),
            position = json.optInt("position", 0),
            count = json.optInt("count", 0),
        )
    }

    val FALLBACK_LANGUAGES = listOf(ContentLanguage("es", "Español"), ContentLanguage("en", "English"))

    fun parseLanguages(body: String): List<ContentLanguage> = try {
        val list = JSONObject(body).getJSONArray("languages")
        (0 until list.length()).map { list.getJSONObject(it) }
            .map { ContentLanguage(it.optString("code", ""), it.optString("name", "")) }
            .filter { it.code.isNotEmpty() }
            .ifEmpty { FALLBACK_LANGUAGES }
    } catch (e: JSONException) {
        FALLBACK_LANGUAGES
    }

    private fun get(url: String): String {
        val connection = try {
            URL(url).openConnection() as HttpURLConnection
        } catch (e: IOException) {
            throw ServerException(Problem.CONNECTION, e.message ?: "")
        }
        try {
            connection.connectTimeout = 30_000
            connection.readTimeout = 60_000
            connection.instanceFollowRedirects = true
            val status = connection.responseCode
            if (status == 404) throw ServerException(Problem.NO_IMAGE, "There is no image for this day")
            if (status != 200) throw ServerException(Problem.HTTP, "HTTP $status")
            return connection.inputStream.bufferedReader().use { it.readText() }
        } catch (e: IOException) {
            throw ServerException(Problem.CONNECTION, e.message ?: "")
        } finally {
            connection.disconnect()
        }
    }

    suspend fun fetchArtwork(url: String): Artwork = withContext(Dispatchers.IO) { parseArtwork(get(url)) }

    suspend fun fetchLanguages(base: String): List<ContentLanguage> = withContext(Dispatchers.IO) {
        try {
            parseLanguages(get(languagesUrl(base)))
        } catch (e: ServerException) {
            FALLBACK_LANGUAGES
        }
    }

    /** Only http(s) sources are opened (never javascript: and the like). */
    fun isWebLink(url: String) = url.lowercase().let { it.startsWith("http://") || it.startsWith("https://") }
}
