package com.veil.guard.wire.ml

import com.veil.brain.contract.Rect
import kotlin.math.floor
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

data class Img(val px: IntArray, val w: Int, val h: Int)

/** Pure pixel helpers for the ONNX adapters. */
object ImagePrep {
    /** Crop a screen-px rect out of a frame-size ARGB buffer (screen to frame scale, clamped, at least 1x1). */
    fun crop(argb: IntArray, fw: Int, fh: Int, sw: Int, sh: Int, r: Rect): Img {
        val x0 = (r.x * fw.toDouble() / sw).toInt().coerceIn(0, fw - 1)
        val y0 = (r.y * fh.toDouble() / sh).toInt().coerceIn(0, fh - 1)
        val x1 = (((r.x + r.w) * fw.toDouble() / sw).toInt()).coerceIn(x0 + 1, fw)
        val y1 = (((r.y + r.h) * fh.toDouble() / sh).toInt()).coerceIn(y0 + 1, fh)
        val w = x1 - x0
        val h = y1 - y0
        val out = IntArray(w * h)
        for (y in 0 until h) System.arraycopy(argb, (y0 + y) * fw + x0, out, y * w, w)
        return Img(out, w, h)
    }

    /** PIL BILINEAR-style (pixel-centre) sampling without antialias. */
    fun resizeBilinear(img: Img, tw: Int, th: Int): Img {
        val out = IntArray(tw * th)
        val sx = img.w.toDouble() / tw
        val sy = img.h.toDouble() / th
        for (y in 0 until th) {
            val fy = ((y + 0.5) * sy - 0.5).coerceIn(0.0, img.h - 1.0)
            val y0 = floor(fy).toInt()
            val y1 = min(y0 + 1, img.h - 1)
            val wy = fy - y0
            for (x in 0 until tw) {
                val fx = ((x + 0.5) * sx - 0.5).coerceIn(0.0, img.w - 1.0)
                val x0 = floor(fx).toInt()
                val x1 = min(x0 + 1, img.w - 1)
                val wx = fx - x0
                var v = 0xFF shl 24
                for (sh in intArrayOf(16, 8, 0)) {
                    val a = (img.px[y0 * img.w + x0] shr sh) and 255
                    val b = (img.px[y0 * img.w + x1] shr sh) and 255
                    val c = (img.px[y1 * img.w + x0] shr sh) and 255
                    val d = (img.px[y1 * img.w + x1] shr sh) and 255
                    val top = a + (b - a) * wx
                    val bot = c + (d - c) * wx
                    v = v or ((top + (bot - top) * wy).roundToInt().coerceIn(0, 255) shl sh)
                }
                out[y * tw + x] = v
            }
        }
        return Img(out, tw, th)
    }

    /** nudenet/parity.py preprocess: black square canvas, image at (0,0), resize to size. Params = (scale, padX, padY). */
    fun letterbox(img: Img, size: Int): Pair<Img, Triple<Float, Float, Float>> {
        val side = max(img.w, img.h)
        val canvas = IntArray(side * side) { 0xFF shl 24 }
        for (y in 0 until img.h) System.arraycopy(img.px, y * img.w, canvas, y * side, img.w)
        val scale = size.toFloat() / side
        return resizeBilinear(Img(canvas, side, side), size, size) to Triple(scale, 0f, 0f)
    }

    /** RGB planes into out at off: (v/255 - mean)/std. */
    fun chw(img: Img, mean: Float, std: Float, out: FloatArray, off: Int) {
        val n = img.w * img.h
        for (i in 0 until n) {
            val p = img.px[i]
            out[off + i] = (((p shr 16) and 255) / 255f - mean) / std
            out[off + n + i] = (((p shr 8) and 255) / 255f - mean) / std
            out[off + 2 * n + i] = ((p and 255) / 255f - mean) / std
        }
    }
}
