package com.veil.conductor.video

import com.veil.brain.contract.Finding
import com.veil.brain.contract.FrameMeta
import com.veil.brain.contract.Rect
import com.veil.conductor.Frame
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class HoldDismissTest {
    private fun frame(fill: (Int, Int) -> Int): Frame {
        val w = 100
        val h = 200
        val argb = IntArray(w * h) { i -> fill(i % w, i / w) }
        return Frame(FrameMeta(1, 0, w, h, 1000, 2000, emptyList()), ByteArray(0), argb)
    }

    private fun hide(r: Rect, lane: String = "describer", decision: String = "hide") =
        Finding("f", 1, 1, 0, "bison", 2, decision, 1.0, r, "object", lane)

    private val pic = Rect(100, 200, 600, 400)
    private val still = frame { x, y -> if (x in 10..70 && y in 20..60) 0xFF884422.toInt() else 0xFFFFFFFF.toInt() }

    @Test
    fun unchangedPictureStaysCoveredWhenALookIsUnsure() {
        val s = StillHold()
        s.apply(listOf(hide(pic)), still, 1, 0)
        // Next looks: only a near-miss (or nothing) for the same, unchanged picture: still covered.
        val out = s.apply(listOf(hide(pic, decision = "nearMiss")), still, 2, 400)
        assertTrue(out.any { it.decision == "hide" && it.lane == "hold" && it.rect == pic })
        assertTrue(s.apply(emptyList(), still, 3, 800).any { it.lane == "hold" })
    }

    @Test
    fun coverGoesWhenThePictureChanges() {
        val s = StillHold()
        s.apply(listOf(hide(pic)), still, 1, 0)
        val other = frame { _, _ -> 0xFF101010.toInt() } // scrolled away / new page
        assertTrue(s.apply(emptyList(), other, 2, 400).none { it.lane == "hold" })
    }

    @Test
    fun continueOnAVideoStopsCoveringItUntilItStopsPlaying() {
        val d = Dismissals(videoGoneMs = 8000)
        val player = Rect(0, 200, 1440, 810)
        d.add(player, video = true, tMs = 0)
        val vid = hide(player, lane = "video")
        assertEquals(0, d.apply(listOf(vid), listOf(player), 1000).size)
        // Moved to the mini player: still dismissed.
        val mini = Rect(800, 2600, 600, 340)
        assertEquals(0, d.apply(listOf(hide(mini, lane = "video")), listOf(mini), 2000).size)
        // Nothing playing for > 8 s (video ended / new video after a pause): warns again.
        d.apply(emptyList(), emptyList(), 5000)
        assertEquals(1, d.apply(listOf(vid), listOf(player), 11_000).size)
    }

    @Test
    fun continueOnAStillPictureLastsWhileItIsOnScreen() {
        val d = Dismissals(stillGoneMs = 2500)
        d.add(pic, video = false, tMs = 0)
        assertEquals(0, d.apply(listOf(hide(pic)), emptyList(), 1000).size)
        assertEquals(1, d.apply(listOf(hide(Rect(100, 1500, 600, 400))), emptyList(), 1500).size) // another one
        d.apply(emptyList(), emptyList(), 2000)
        assertEquals(1, d.apply(listOf(hide(pic)), emptyList(), 5000).size) // gone for > 2.5 s: covered again
    }
}
