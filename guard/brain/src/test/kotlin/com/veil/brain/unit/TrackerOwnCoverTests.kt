package com.veil.brain.unit

import com.veil.brain.contract.Rect
import com.veil.brain.cover.Tracker
import org.junit.Assert.assertEquals
import org.junit.Test

class TrackerOwnCoverTests {
    private fun hide(rect: Rect): Map<String, Any?> = mapOf(
        "findingId" to "f1",
        "conceptId" to "cats",
        "layer" to 2,
        "decision" to "hide",
        "rect" to rect.toMap(),
        "scope" to "object"
    )

    @Test
    fun trackUnderOwnCoverIsHeldPastHold() {
        val r = Rect(100, 300, 200, 200)
        val tr = Tracker("balanced")
        tr.onFindings(listOf(hide(r)), 0)
        assertEquals(1, tr.tick(0, emptyList()).size)
        // Past hold (1500 ms) with our own cover over it: the grey frame says "clean", the track stays.
        assertEquals(1, tr.tick(3000, listOf(r)).size)
        // Past hold with no cover of ours: released.
        assertEquals(0, Tracker("balanced").apply { onFindings(listOf(hide(r)), 0) }.tick(3000, emptyList()).size)
    }

    @Test
    fun heldTrackEndsAtMaxHoldAndOnClear() {
        val r = Rect(100, 300, 200, 200)
        val tr = Tracker("balanced")
        tr.onFindings(listOf(hide(r)), 0)
        assertEquals(1, tr.tick(19_000, listOf(r)).size)
        assertEquals(0, tr.tick(20_001, listOf(r)).size)
        tr.onFindings(listOf(hide(r)), 21_000)
        tr.clear()
        assertEquals(0, tr.tick(22_000, listOf(r)).size)
    }
}
