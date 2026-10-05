package com.veil.guard.wire

import com.veil.guard.overlay.CoverStyle
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class PlanRecordsTest {
    private fun plan() = mapOf(
        "planId" to 7L,
        "tMs" to 100,
        "screenWidth" to 1080,
        "screenHeight" to 2400,
        "rotation" to 0,
        "reason" to "x",
        "masks" to listOf(
            mapOf(
                "maskId" to 1,
                "rect" to mapOf("x" to 10, "y" to 20, "w" to 30L, "h" to 40),
                "style" to "blur",
                "layer" to 2,
                "peekable" to true,
                "label" to "a"
            ),
            mapOf("maskId" to 2L, "rect" to mapOf("x" to 1L, "y" to 2, "w" to 3, "h" to 4), "style" to "solid")
        )
    )

    @Test
    fun roundTrip() {
        val p = PlanRecords.toCoverPlan(plan())
        assertEquals(7L, p.planId)
        assertEquals(2, p.covers.size)
        assertEquals(CoverStyle.BLUR, p.covers[0].style)
        assertEquals(30, p.covers[0].rect.w)
        assertTrue(p.covers[0].peekable)
        assertEquals(2, p.covers[1].maskId)
    }

    @Test
    fun shiftAndEmpty() {
        val s = PlanRecords.shifted(PlanRecords.toCoverPlan(plan()), 5, -3)
        assertEquals(15, s.covers[0].rect.x)
        assertEquals(17, s.covers[0].rect.y)
        val e = PlanRecords.toCoverPlan(PlanRecords.empty(9, 1, 100, 200))
        assertTrue(e.covers.isEmpty())
        assertEquals("clear", e.reason)
    }
}
