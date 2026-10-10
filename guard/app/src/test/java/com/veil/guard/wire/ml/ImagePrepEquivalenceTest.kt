package com.veil.guard.wire.ml

import com.veil.guard.wire.ml.accel.BatchPlan
import java.util.Random
import kotlin.math.floor
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** The pre-optimisation implementations, kept verbatim as the reference. */
private object Legacy {
    fun resize(img: Img, tw: Int, th: Int): Img {
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

    fun letterbox(img: Img, size: Int): Img {
        val side = max(img.w, img.h)
        val canvas = IntArray(side * side) { 0xFF shl 24 }
        for (y in 0 until img.h) System.arraycopy(img.px, y * img.w, canvas, y * side, img.w)
        return resize(Img(canvas, side, side), size, size)
    }

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

class ImagePrepEquivalenceTest {
    private fun rand(w: Int, h: Int, seed: Long): Img {
        val r = Random(seed)
        return Img(IntArray(w * h) { (0xFF shl 24) or r.nextInt(0x1000000) }, w, h)
    }

    @Test
    fun resizeIdentical() {
        for ((w, h) in listOf(300 to 200, 37 to 91, 500 to 500, 5 to 7, 1 to 1)) {
            val img = rand(w, h, w * 31L + h)
            assertArrayEquals("$w x $h", Legacy.resize(img, 224, 224).px, ImagePrep.resizeBilinear(img, 224, 224).px)
        }
    }

    @Test
    fun letterboxIdentical() {
        for ((w, h) in listOf(300 to 200, 200 to 300, 120 to 120, 53 to 97)) {
            val img = rand(w, h, w * 7L + h)
            assertArrayEquals("$w x $h", Legacy.letterbox(img, 320).px, ImagePrep.letterbox(img, 320).first.px)
        }
    }

    @Test
    fun chwIdentical() {
        val img = rand(16, 9, 5)
        val a = FloatArray(3 * 16 * 9 + 4)
        val b = FloatArray(a.size)
        Legacy.chw(img, 0.5f, 0.5f, a, 4)
        ImagePrep.chw(img, 0.5f, 0.5f, b, 4)
        assertArrayEquals(a, b, 0f)
        Legacy.chw(img, 0f, 1f, a, 0)
        ImagePrep.chw(img, 0f, 1f, b, 0)
        assertArrayEquals(a, b, 0f)
    }

    @Test
    fun batchPlanAvoidsPadding() {
        val all = listOf(1, 4, 16)
        assertEquals(listOf(16, 4, 1, 1), BatchPlan.plan(22, all))
        assertEquals(listOf(16), BatchPlan.plan(16, all))
        assertEquals(listOf(4), BatchPlan.plan(4, all))
        assertEquals(listOf(1), BatchPlan.plan(1, all))
        assertEquals(listOf(4, 1), BatchPlan.plan(5, all))
        assertEquals(listOf(16), BatchPlan.plan(14, all))
        assertEquals(listOf(16, 16), BatchPlan.plan(22, listOf(16)))
        assertEquals(listOf(4, 4, 4), BatchPlan.plan(10, listOf(4)))
        assertEquals(emptyList<Int>(), BatchPlan.plan(0, all))
        assertEquals(emptyList<Int>(), BatchPlan.plan(3, emptyList()))
        for (n in 1..40) assertTrue(BatchPlan.plan(n, all).sum() >= n)
    }
}
