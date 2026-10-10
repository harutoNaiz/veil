package com.veil.guard.wire

import android.graphics.Bitmap
import com.google.android.gms.tasks.Tasks
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.latin.TextRecognizerOptions
import com.veil.brain.contract.Rect
import com.veil.conductor.Frame
import com.veil.conductor.Ocr

/** Bundled Latin ML Kit OCR over a crop of frame.argb. Call off the main thread (runs on the AI worker). */
class MlKitOcr : Ocr {
    private val client by lazy { TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS) }

    override fun read(frame: Frame, rect: Rect): String? {
        val argb = frame.argb ?: return null
        val m = frame.meta
        val sx = m.width.toFloat() / m.screenWidth
        val sy = m.height.toFloat() / m.screenHeight
        val b =
            ocrBox(
                (rect.x * sx).toInt(),
                (rect.y * sy).toInt(),
                (rect.w * sx).toInt(),
                (rect.h * sy).toInt(),
                m.width,
                m.height
            )
                ?: return null
        val full = Bitmap.createBitmap(argb, m.width, m.height, Bitmap.Config.ARGB_8888)
        val crop = Bitmap.createBitmap(full, b[0], b[1], b[2], b[3])
        val text = Tasks.await(client.process(InputImage.fromBitmap(crop, 0))).text
        return text.ifBlank { null }
    }
}

/** ML Kit throws below this side length. */
internal const val MIN_OCR_SIDE = 32

/**
 * Clamps a frame-pixel box into the frame and grows it (about its centre, kept inside) to at least
 * [MIN_OCR_SIDE] a side. Null when the frame itself is too small. Returns [x, y, w, h].
 */
internal fun ocrBox(x: Int, y: Int, w: Int, h: Int, fw: Int, fh: Int): IntArray? {
    if (fw < MIN_OCR_SIDE || fh < MIN_OCR_SIDE) return null
    fun axis(p: Int, len: Int, full: Int): IntArray {
        val a = p.coerceIn(0, full - 1)
        val b = (p + maxOf(len, 1)).coerceIn(a + 1, full)
        val n = maxOf(b - a, MIN_OCR_SIDE)
        val s = (a - (n - (b - a)) / 2).coerceIn(0, full - n)
        return intArrayOf(s, n)
    }
    val ax = axis(x, w, fw)
    val ay = axis(y, h, fh)
    return intArrayOf(ax[0], ay[0], ax[1], ay[1])
}
