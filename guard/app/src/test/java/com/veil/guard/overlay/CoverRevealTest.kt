package com.veil.guard.overlay

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class CoverRevealTest {
    private val area = 1440L * 3168
    private fun cover(id: Int) = Cover(id, Px(0, 0, 1, 1), CoverStyle.BLUR, 2, false, null, emptyList())
    private val box = Px(100, 500, 800, 600)

    @Test
    fun revealedCoverFadesOutAndStaysGoneWhileFound() {
        val s = CoverSmoother()
        s.onPlan(listOf(cover(1) to box), area, 0)
        val id = s.frame(500)[0].cover.maskId
        s.reveal(id, 600)
        assertEquals(setOf(id), s.revealedIds())
        val fading = s.frame(690)
        assertEquals(1, fading.size)
        assertTrue(!fading[0].live && fading[0].alpha < 1f)
        assertTrue(s.animating(690))
        s.onPlan(listOf(cover(2) to Px(110, 510, 790, 590)), area, 1000)
        assertEquals(0, s.frame(1100).size)
        assertTrue(!s.animating(1100))
    }

    @Test
    fun revealIsForgottenWhenCoverDisappears() {
        val s = CoverSmoother()
        s.onPlan(listOf(cover(1) to box), area, 0)
        s.reveal(s.frame(500)[0].cover.maskId, 600)
        s.onPlan(emptyList(), area, 1000)
        assertTrue(s.revealedIds().isEmpty())
        s.onPlan(listOf(cover(3) to box), area, 2000)
        assertEquals(1, s.frame(2500).size)
    }
}
