package com.veil.guard.capture.blind

import com.veil.guard.capture.PxRect
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class BlindSpotDetectorTest {
    private val w = 360
    private val h = 800

    private fun frame(fill: Int = 200) = ByteArray(w * h) { fill.toByte() }

    private fun blackBox(f: ByteArray, x: Int, y: Int, bw: Int, bh: Int) {
        for (yy in y until y + bh) for (xx in x until x + bw) f[yy * w + xx] = 0
    }

    @Test
    fun allBlackIsFullRect() {
        assertEquals(listOf(PxRect(0, 0, w, h)), BlindSpotDetector.detect(frame(0), w, h, emptyList()))
    }

    @Test
    fun blackVideoHintIsReported() {
        val f = frame()
        blackBox(f, 0, 100, w, 200)
        val hint = PxRect(0, 100, w, 200)
        assertEquals(listOf(hint), BlindSpotDetector.detect(f, w, h, listOf(hint)))
    }

    @Test
    fun brightHintIsIgnored() {
        assertTrue(BlindSpotDetector.detect(frame(), w, h, listOf(PxRect(0, 100, w, 200))).isEmpty())
    }

    @Test
    fun smallBlackIconIgnored() {
        val f = frame()
        blackBox(f, 20, 20, 48, 48)
        assertTrue(BlindSpotDetector.detect(f, w, h, emptyList()).isEmpty())
    }

    @Test
    fun largeBlackRegionBoundingBox() {
        val f = frame()
        blackBox(f, 0, 200, w, 300)
        val r = BlindSpotDetector.detect(f, w, h, emptyList())
        assertEquals(1, r.size)
        assertEquals(PxRect(0, 200, w, 296), r[0])
    }

    @Test
    fun atMostSixteenRects() {
        val hints = (0 until 30).map { PxRect(0, it * 20, 10, 10) }
        val f = frame()
        for (hint in hints) blackBox(f, hint.x, hint.y, hint.w, hint.h)
        assertEquals(16, BlindSpotDetector.detect(f, w, h, hints).size)
    }
}
