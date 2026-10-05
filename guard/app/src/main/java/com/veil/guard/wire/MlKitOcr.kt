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
        val x = (rect.x * sx).toInt().coerceIn(0, m.width - 1)
        val y = (rect.y * sy).toInt().coerceIn(0, m.height - 1)
        val w = (rect.w * sx).toInt().coerceIn(1, m.width - x)
        val h = (rect.h * sy).toInt().coerceIn(1, m.height - y)
        val full = Bitmap.createBitmap(argb, m.width, m.height, Bitmap.Config.ARGB_8888)
        val crop = Bitmap.createBitmap(full, x, y, w, h)
        val text = Tasks.await(client.process(InputImage.fromBitmap(crop, 0))).text
        return text.ifBlank { null }
    }
}
