package com.veil.guard.overlay

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class PlanDiffTest {
    private fun cover(id: Int, x: Int = 0, style: CoverStyle = CoverStyle.SOLID) =
        Cover(id, Px(x, 0, 10, 10), style, 1, false)

    private fun plan(vararg c: Cover) = CoverPlan(1, 0, 100, 200, 0, c.toList(), "t")

    @Test
    fun identicalPlanIsEmpty() {
        assertTrue(PlanDiff.diff(plan(cover(1)), plan(cover(1))).isEmpty)
    }

    @Test
    fun addedRemovedMovedRestyled() {
        val d = PlanDiff.diff(
            plan(cover(1), cover(2), cover(3)),
            plan(cover(1, x = 5), cover(3, style = CoverStyle.BLUR), cover(4))
        )
        assertEquals(listOf(4), d.added.map { it.maskId })
        assertEquals(listOf(2), d.removed)
        assertEquals(listOf(1, 3), d.changed.map { it.maskId })
    }

    @Test
    fun nullOldAddsAll() {
        assertEquals(2, PlanDiff.diff(null, plan(cover(1), cover(2))).added.size)
    }
}
