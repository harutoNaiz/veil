package com.veil.conductor.video

import com.veil.brain.contract.Finding
import com.veil.brain.contract.Rect
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class VideoTest {
    private val tw = 32
    private val th = 64

    private fun frame(i: Int, rect: IntArray? = null, all: Boolean = false): ByteArray {
        val b = ByteArray(tw * th) { 100 }
        for (y in 0 until th) {
            for (x in 0 until tw) {
                val inR = rect != null && x >= rect[0] && x < rect[2] && y >= rect[1] && y < rect[3]
                if (all || inR) b[y * tw + x] = (if (i % 2 == 0) 40 else 200).toByte()
            }
        }
        return b
    }

    @Test fun flickerRectGivesRegion() {
        val v = VideoRegions(1000, 2000)
        for (i in 0 until 8) v.onFrame(frame(i, intArrayOf(4, 16, 28, 40)), tw, th, i * 200L)
        val r = v.regions()
        assertEquals(1, r.size)
        assertEquals(Rect(125, 500, 750, 750), r[0])
    }

    @Test fun scrollGivesNoRegion() {
        val v = VideoRegions(1000, 2000)
        for (i in 0 until 8) v.onFrame(frame(i, all = true), tw, th, i * 200L)
        assertTrue(v.regions().isEmpty())
    }

    private fun f(id: String, d: String, r: Rect) = Finding(id, 1, 1, 0, "tiger", 2, d, 0.9, r, "object", "x")

    @Test fun sticky() {
        val region = Rect(100, 500, 800, 600)
        val s = StickyVideo()
        val out = s.apply(listOf(f("a", "hide", Rect(300, 600, 100, 100))), listOf(region), 1, 0)
        assertEquals(1, out.size)
        assertEquals(region, out[0].rect)
        assertEquals("video", out[0].lane)
        assertEquals("tiger", out[0].conceptId)
        for (k in 1..3) {
            assertEquals(1, s.apply(emptyList(), listOf(region), 1 + k, k * 1000L).size)
        }
        assertEquals(0, s.apply(emptyList(), listOf(region), 5, 3500L).size)
    }

    @Test fun outsidePassesThrough() {
        val s = StickyVideo()
        val x = f("a", "hide", Rect(0, 0, 50, 50))
        assertEquals(listOf(x), s.apply(listOf(x), listOf(Rect(100, 500, 800, 600)), 1, 0))
    }
}
