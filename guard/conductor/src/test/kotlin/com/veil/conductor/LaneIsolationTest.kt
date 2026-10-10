package com.veil.conductor

import com.veil.brain.contract.Finding
import com.veil.brain.contract.FrameMeta
import com.veil.brain.contract.Rect
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class LaneIsolationTest {
    private val input =
        LookInput(
            1,
            Frame(FrameMeta(1, 1000, 360, 800, 720, 1600, emptyList()), ByteArray(0)),
            Rect(0, 0, 10, 10),
            emptyList(),
            "balanced"
        )
    private val nsfw = Finding("f1", 1, 1, 1000, "nudity", 1, "hide", 0.9, Rect(0, 0, 10, 10), "object", "nudenet")
    private val good = Lane { listOf(nsfw) }
    private val bad = Lane { throw ArrayIndexOutOfBoundsException("length=8 index=8") }

    @Test fun throwingLaneKeepsOthersFindings() {
        val warns = ArrayList<Map<String, Any?>>()
        val out = runLanesIsolated(listOf(bad, good, bad), input) { warns.add(it) }
        assertEquals(listOf(nsfw), out)
        assertEquals(2, warns.size)
        assertEquals("warn", warns[0]["kind"])
        assertEquals("lane-failed", warns[0]["what"])
        assertTrue(warns[0]["why"].toString().contains("index=8"))
        assertTrue((warns[0]["lane"] as String).isNotEmpty())
    }

    @Test fun nullLogIsFine() {
        assertEquals(listOf(nsfw), runLanesIsolated(listOf(bad, good), input, null))
    }
}
