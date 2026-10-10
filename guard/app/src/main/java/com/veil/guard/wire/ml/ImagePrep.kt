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
    fun resizeBilinear(img: Img, tw: Int, th: Int): Img = resizePadded(img, img.w, img.h, tw, th)

    /**
     * Bilinear resize of img placed at (0,0) on a virtual vw x vh canvas; pixels outside img read as opaque black.
     * Same maths as sampling a materialised canvas, without allocating it.
     */
    fun resizePadded(img: Img, vw: Int, vh: Int, tw: Int, th: Int): Img {
        val out = IntArray(tw * th)
        val sx = vw.toDouble() / tw
        val sy = vh.toDouble() / th
        val x0s = IntArray(tw)
        val x1s = IntArray(tw)
        val wxs = DoubleArray(tw)
        for (x in 0 until tw) {
            val fx = ((x + 0.5) * sx - 0.5).coerceIn(0.0, vw - 1.0)
            val x0 = floor(fx).toInt()
            x0s[x] = x0
            x1s[x] = min(x0 + 1, vw - 1)
            wxs[x] = fx - x0
        }
        val iw = img.w
        val ih = img.h
        val px = img.px
        for (y in 0 until th) {
            val fy = ((y + 0.5) * sy - 0.5).coerceIn(0.0, vh - 1.0)
            val y0 = floor(fy).toInt()
            val y1 = min(y0 + 1, vh - 1)
            val wy = fy - y0
            val r0 = y0 * iw
            val r1 = y1 * iw
            val in0 = y0 < ih
            val in1 = y1 < ih
            val o = y * tw
            for (x in 0 until tw) {
                val xa = x0s[x]
                val xb = x1s[x]
                val wx = wxs[x]
                val p00 = if (in0 && xa < iw) px[r0 + xa] else BLACK
                val p01 = if (in0 && xb < iw) px[r0 + xb] else BLACK
                val p10 = if (in1 && xa < iw) px[r1 + xa] else BLACK
                val p11 = if (in1 && xb < iw) px[r1 + xb] else BLACK
                var v = BLACK
                var sh = 16
                while (sh >= 0) {
                    val a = (p00 shr sh) and 255
                    val c = (p10 shr sh) and 255
                    val top = a + (((p01 shr sh) and 255) - a) * wx
                    val bot = c + (((p11 shr sh) and 255) - c) * wx
                    v = v or ((top + (bot - top) * wy).roundToInt().coerceIn(0, 255) shl sh)
                    sh -= 8
                }
                out[o + x] = v
            }
        }
        return Img(out, tw, th)
    }

    /** nudenet/parity.py preprocess: black square canvas, image at (0,0), resize to size. Params = (scale, padX, padY). */
    fun letterbox(img: Img, size: Int): Pair<Img, Triple<Float, Float, Float>> {
        val side = max(img.w, img.h)
        val scale = size.toFloat() / side
        return resizePadded(img, side, side, size, size) to Triple(scale, 0f, 0f)
    }

    /** RGB planes into out at off: (v/255 - mean)/std. */
    fun chw(img: Img, mean: Float, std: Float, out: FloatArray, off: Int) {
        val n = img.w * img.h
        val lut = FloatArray(256) { (it / 255f - mean) / std }
        val px = img.px
        for (i in 0 until n) {
            val p = px[i]
            out[off + i] = lut[(p shr 16) and 255]
            out[off + n + i] = lut[(p shr 8) and 255]
            out[off + 2 * n + i] = lut[p and 255]
        }
    }

    private const val BLACK = 0xFF shl 24
}
