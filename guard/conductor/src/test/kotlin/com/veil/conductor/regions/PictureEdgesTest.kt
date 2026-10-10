package com.veil.conductor.regions

import com.veil.brain.contract.FrameMeta
import com.veil.brain.contract.Rect
import com.veil.brain.gate.THUMB_H
import com.veil.brain.gate.THUMB_W
import com.veil.conductor.Frame
import org.junit.Assert.assertTrue
import org.junit.Test

class PictureEdgesTest {
    /** 360x792 frame (screen 1440x3168): white page with two textured photos side by side and a 12 px gutter. */
    private fun page(): Frame {
        val w = 360
        val h = 792
        val px = IntArray(w * h) { 0xFFFFFFFF.toInt() }
        fun photo(x0: Int, y0: Int, pw: Int, ph: Int) {
            for (y in y0 until y0 + ph) {
                for (x in x0 until x0 + pw) {
                    val v = 60 + ((x * 37 + y * 61) % 120) // texture, never flat
                    px[y * w + x] = (0xFF shl 24) or (v shl 16) or ((v / 2) shl 8) or (v / 3)
                }
            }
        }
        photo(4, 100, 170, 120)
        photo(186, 100, 170, 120)
        return Frame(FrameMeta(1, 0, w, h, 1440, 3168, emptyList()), ByteArray(THUMB_W * THUMB_H), px)
    }

    @Test
    fun objectBoxGrowsToItsPhotoAndStopsAtTheGutter() {
        // Animal box inside the left photo (screen px = frame px * 4).
        val snapped = PictureEdges.snap(page(), Rect(60 * 4, 130 * 4, 60 * 4, 50 * 4))
        // Left photo in screen px: x 16..696, y 400..880.
        assertTrue("left $snapped", snapped.x in 8..24)
        assertTrue("top $snapped", snapped.y in 392..408)
        assertTrue("right ${snapped.x + snapped.w}", snapped.x + snapped.w in 688..704)
        assertTrue("bottom ${snapped.y + snapped.h}", snapped.y + snapped.h in 872..888)
    }

    @Test
    fun noPixelsLeavesTheBoxAlone() {
        val f = page().let { Frame(it.meta, it.thumb, null) }
        val r = Rect(240, 520, 240, 200)
        assertTrue(PictureEdges.snap(f, r) == r)
    }
}
