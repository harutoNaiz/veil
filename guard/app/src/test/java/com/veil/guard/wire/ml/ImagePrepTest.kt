package com.veil.guard.wire.ml

import com.veil.brain.contract.Rect
import org.junit.Assert.assertEquals
import org.junit.Test

class ImagePrepTest {
    private fun rgb(r: Int, g: Int, b: Int) = (0xFF shl 24) or (r shl 16) or (g shl 8) or b

    @Test
    fun cropScalesAndClamps() {
        val px = IntArray(100 * 200) { it }
        val c = ImagePrep.crop(px, 100, 200, 1000, 2000, Rect(100, 200, 300, 400))
        assertEquals(30, c.w)
        assertEquals(40, c.h)
        assertEquals(20 * 100 + 10, c.px[0])
        val d = ImagePrep.crop(px, 100, 200, 1000, 2000, Rect(900, 1900, 500, 500))
        assertEquals(10, d.w)
        assertEquals(10, d.h)
    }

    @Test
    fun letterboxParams() {
        val (img, lb) = ImagePrep.letterbox(Img(IntArray(300 * 200) { rgb(255, 255, 255) }, 300, 200), 320)
        assertEquals(320, img.w)
        assertEquals(320f / 300f, lb.first, 1e-6f)
        assertEquals(0f, lb.second, 0f)
        assertEquals(rgb(255, 255, 255), img.px[0])
        assertEquals(rgb(0, 0, 0), img.px[319 * 320 + 160])
    }

    @Test
    fun chwPlanes() {
        val img = Img(intArrayOf(rgb(255, 0, 0), rgb(0, 255, 0), rgb(0, 0, 255), rgb(255, 255, 255)), 2, 2)
        val out = FloatArray(12)
        ImagePrep.chw(img, 0.5f, 0.5f, out, 0)
        assertEquals(1f, out[0], 1e-6f)
        assertEquals(-1f, out[1], 1e-6f)
        assertEquals(1f, out[4 + 1], 1e-6f)
        assertEquals(1f, out[8 + 2], 1e-6f)
        assertEquals(1f, out[11], 1e-6f)
    }

    @Test
    fun bilinear4to2() {
        val px = IntArray(16) { rgb(it * 10, 0, 0) }
        val o = ImagePrep.resizeBilinear(Img(px, 4, 4), 2, 2)
        assertEquals(25, (o.px[0] shr 16) and 255)
        assertEquals(125, (o.px[3] shr 16) and 255)
    }
}
