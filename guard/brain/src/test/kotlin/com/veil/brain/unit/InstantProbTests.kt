package com.veil.brain.unit

import com.veil.brain.contract.Rect
import com.veil.brain.cover.TRACK_MODES
import com.veil.brain.cover.Tracker
import org.junit.Assert.assertEquals
import org.junit.Test

class InstantProbTests {
    private val r = Rect(100, 300, 200, 200)

    private fun hide(prob: Double, lane: String = "image"): Map<String, Any?> = mapOf(
        "findingId" to "f1",
        "conceptId" to "cats",
        "layer" to 2,
        "decision" to "hide",
        "probability" to prob,
        "rect" to r.toMap(),
        "scope" to "object",
        "lane" to lane
    )

    private fun tracker(instant: Double) =
        Tracker("balanced", p = TRACK_MODES.getValue("balanced").copy(instantProb = instant))

    private fun confirmed(tr: Tracker, t: Long) = tr.tick(t, emptyList()).count { it["state"] == "confirmed" }

    @Test
    fun confidentFirstLookIsCoveredAtOnce() {
        val tr = tracker(0.97)
        tr.onFindings(listOf(hide(0.99)), 0)
        assertEquals(1, confirmed(tr, 0))
    }

    @Test
    fun borderlineNeedsTwoLooks() {
        val tr = tracker(0.97)
        tr.onFindings(listOf(hide(0.8)), 0)
        assertEquals(0, confirmed(tr, 0))
        tr.onFindings(listOf(hide(0.8)), 500)
        assertEquals(1, confirmed(tr, 500))
    }

    @Test
    fun videoLaneIsInstantWhenEnabled() {
        val tr = tracker(0.97)
        tr.onFindings(listOf(hide(0.5, "video")), 0)
        assertEquals(1, confirmed(tr, 0))
    }

    @Test
    fun defaultParamsUnchanged() {
        val tr = Tracker("balanced")
        tr.onFindings(listOf(hide(0.99, "video")), 0)
        assertEquals(0, confirmed(tr, 0))
        tr.onFindings(listOf(hide(0.99)), 500)
        assertEquals(1, confirmed(tr, 500))
    }
}
