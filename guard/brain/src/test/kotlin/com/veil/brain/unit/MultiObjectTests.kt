package com.veil.brain.unit

import com.veil.brain.contract.Rect
import com.veil.brain.cover.Tracker
import com.veil.brain.cover.plan
import org.junit.Assert.assertEquals
import org.junit.Test

/** A real phone screen (1440x3168) with six separate objects: every one is tracked and covered on its own. */
class MultiObjectTests {
    private val bison =
        listOf(
            Rect(86, 2702, 614, 305),
            Rect(221, 1942, 485, 462),
            Rect(730, 1816, 637, 701),
            Rect(258, 1179, 353, 402),
            Rect(851, 1249, 464, 301),
            Rect(877, 2712, 407, 272)
        )

    private fun hide(i: Int, r: Rect): Map<String, Any?> = mapOf(
        "findingId" to "f$i",
        "conceptId" to "bison",
        "layer" to 2,
        "decision" to "hide",
        "rect" to r.toMap(),
        "scope" to "object"
    )

    @Test
    fun everyObjectOnABigScreenIsCovered() {
        val tr = Tracker("strict").apply { resize(1440, 3168) }
        tr.onFindings(bison.mapIndexed { i, r -> hide(i, r) }, 0)
        val tracks = tr.tick(0, emptyList())
        assertEquals(6, tracks.count { it["state"] == "confirmed" })
        @Suppress("UNCHECKED_CAST")
        val masks = plan(tracks, 0, 1, 1440, 3168, "strict", "look")["masks"] as List<*>
        assertEquals(6, masks.size) // separate photos stay separate covers
    }

    @Test
    fun withoutTheRealSizeObjectsBeyondTheTapeScreenWereParked() {
        // The old behaviour (720x1600 tape default) parked everything right of x=720 or below y=1600.
        val tr = Tracker("strict")
        tr.onFindings(bison.mapIndexed { i, r -> hide(i, r) }, 0)
        assertEquals(1, tr.tick(0, emptyList()).count { it["state"] == "confirmed" })
    }
}
