// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later
package es.llana.catholicbackground.wallpaper

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.ColorMatrix
import android.graphics.ColorMatrixColorFilter
import android.graphics.Paint
import android.graphics.Rect
import androidx.core.graphics.createBitmap
import androidx.core.graphics.scale
import kotlin.math.min
import kotlin.math.roundToInt

/**
 * Composes a wallpaper of the size of the screen: the whole artwork, as big as possible,
 * on a blurred copy of it, its average color or a color (the same as the desktop applications).
 */
object Composer {
    /** Position and size of a rectangle (plain numbers, so that it can be tested without Android). */
    data class Box(val left: Int, val top: Int, val width: Int, val height: Int) {
        fun toRect() = Rect(left, top, left + width, top + height)
    }

    /** Largest rectangle with the proportions of the image that fits in the area, centred. */
    fun fit(imageWidth: Int, imageHeight: Int, areaWidth: Int, areaHeight: Int): Box {
        val scale = min(areaWidth.toDouble() / imageWidth, areaHeight.toDouble() / imageHeight)
        val w = (imageWidth * scale).roundToInt().coerceAtLeast(1)
        val h = (imageHeight * scale).roundToInt().coerceAtLeast(1)
        return Box((areaWidth - w) / 2, (areaHeight - h) / 2, w, h)
    }

    fun averageColor(image: Bitmap): Int {
        val pixel = image.scale(1, 1, filter = true)
        return pixel.getPixel(0, 0).also { pixel.recycle() }
    }

    fun compose(image: Bitmap, width: Int, height: Int, mode: String, color: Int): Bitmap {
        val result = createBitmap(width, height)
        val canvas = Canvas(result)
        val paint = Paint(Paint.FILTER_BITMAP_FLAG or Paint.ANTI_ALIAS_FLAG)
        when (mode) {
            "color" -> canvas.drawColor(color)
            "average" -> canvas.drawColor(averageColor(image))
            else -> drawBlurred(canvas, image, width, height)
        }
        canvas.drawBitmap(image, null, fit(image.width, image.height, width, height).toRect(), paint)
        return result
    }

    /** The image enlarged to cover the screen, blurred (shrunk and enlarged again) and slightly darkened. */
    private fun drawBlurred(canvas: Canvas, image: Bitmap, width: Int, height: Int) {
        // Part of the image with the proportions of the screen
        var cropWidth = image.width
        var cropHeight = (image.width.toDouble() * height / width).roundToInt()
        if (cropHeight > image.height) {
            cropHeight = image.height
            cropWidth = (image.height.toDouble() * width / height).roundToInt()
        }
        val crop = Bitmap.createBitmap(image, (image.width - cropWidth) / 2, (image.height - cropHeight) / 2, cropWidth, cropHeight)
        val tinyWidth = 24
        var current = crop.scale(tinyWidth, (tinyWidth.toDouble() * height / width).roundToInt().coerceAtLeast(1), filter = true)
        if (crop !== image) crop.recycle()
        while (current.width * 4 < width) {
            val next = current.scale(current.width * 2, current.height * 2, filter = true)
            current.recycle()
            current = next
        }
        val darken = Paint(Paint.FILTER_BITMAP_FLAG).apply {
            colorFilter = ColorMatrixColorFilter(ColorMatrix().apply { setScale(0.73f, 0.73f, 0.73f, 1f) })
        }
        canvas.drawColor(Color.BLACK)
        canvas.drawBitmap(current, null, Rect(0, 0, width, height), darken)
        current.recycle()
    }

    fun parseColor(hex: String): Int = try {
        Color.parseColor(hex)
    } catch (e: IllegalArgumentException) {
        Color.BLACK
    }
}
