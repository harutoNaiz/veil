package com.veil.guard.overlay

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class CoverSmootherTest {
    private val area = 1440L * 3168
    private fun cover(id: Int, vararg concepts: String) =
        Cover(id, Px(0, 0, 1, 1), CoverStyle.BLUR, 2, false, null, concepts.toList())

    @Test
    fun stillCoverNeverShrinksOrJitters() {
        val s = CoverSmoother()
        val big = Px(0, 400, 1440, 810) // the whole video preview
        s.onPlan(listOf(cover(1) to big), area, 0)
        // Next looks box only part of the playing preview, a bit differently each time.
        s.onPlan(listOf(cover(2) to Px(100, 500, 900, 600)), area, 1000)
        s.onPlan(listOf(cover(3) to Px(300, 450, 1000, 700)), area, 2000)
        val f = s.frame(3000)
        assertEquals(1, f.size)
        assertEquals(big, f[0].rect)
        assertEquals(1, f[0].cover.maskId) // same cover throughout: its texture is reused, no flicker
    }

    @Test
    fun overlappingCoversBecomeOne() {
        val s = CoverSmoother()
        s.onPlan(
            listOf(cover(1, "bison") to Px(20, 1380, 1030, 640), cover(2, "bison") to Px(20, 1900, 900, 700)),
            area,
            0
        )
        val f = s.frame(1000)
        assertEquals(1, f.size)
        assertEquals(Px(20, 1380, 1030, 1220), f[0].rect)
        val apart = CoverSmoother.merge(listOf(cover(1) to Px(0, 0, 100, 100), cover(2) to Px(200, 0, 100, 100)), area)
        assertEquals(2, apart.size)
    }

    @Test
    fun hugeMergeIsRefused() {
        val m = CoverSmoother.merge(listOf(cover(1) to Px(0, 0, 1440, 1500), cover(2) to Px(0, 1400, 1440, 1500)), area)
        assertEquals(2, m.size)
    }

    @Test
    fun coversFollowScrollAtOnceAndSlideToTheNextPlan() {
        val s = CoverSmoother(fadeMs = 100, moveMs = 100)
        s.onPlan(listOf(cover(1) to Px(0, 1000, 600, 400)), area, 0)
        s.onScroll(0, -500, Px(0, 200, 1440, 2800))
        assertEquals(500, s.frame(200)[0].rect.y)
        s.onScroll(0, 1, null) // sign-only jitter event: ignored
        assertEquals(500, s.frame(200)[0].rect.y)
        // Chrome under-reports flings: the next look finds the picture further up; the cover slides there.
        s.onPlan(listOf(cover(1) to Px(0, 300, 600, 400)), area, 300)
        val mid = s.frame(350)[0].rect.y
        assertTrue(mid in 301..499)
        assertEquals(300, s.frame(400)[0].rect.y)
        assertEquals(1, s.frame(400).size)
    }

    @Test
    fun coversOutsideTheScrolledListStay() {
        val s = CoverSmoother()
        s.onPlan(listOf(cover(1) to Px(0, 2000, 300, 300)), area, 0)
        s.onScroll(-400, 0, Px(0, 500, 1440, 600)) // a carousel higher up
        assertEquals(0, s.frame(1000)[0].rect.x)
    }

    @Test
    fun coversFadeInAndOut() {
        val s = CoverSmoother(fadeMs = 200)
        s.onPlan(listOf(cover(1) to Px(0, 0, 500, 500)), area, 0)
        assertEquals(0.5f, s.frame(100)[0].alpha, 0.01f)
        assertEquals(1f, s.frame(300)[0].alpha, 0.01f)
        assertFalse(s.animating(300))
        s.onPlan(emptyList(), area, 400)
        assertTrue(s.animating(450))
        assertEquals(0.5f, s.frame(500)[0].alpha, 0.01f)
        assertTrue(s.frame(600).isEmpty())
    }

    @Test
    fun briefDropDoesNotBlink() {
        val s = CoverSmoother(fadeMs = 200)
        s.onPlan(listOf(cover(1) to Px(0, 0, 500, 500)), area, 0)
        s.onPlan(emptyList(), area, 1000)
        s.onPlan(listOf(cover(1) to Px(0, 0, 500, 500)), area, 1050) // back before it faded out
        val f = s.frame(1300)
        assertEquals(1, f.size)
        assertEquals(1f, f[0].alpha, 0.01f)
        assertEquals(1, f[0].cover.maskId)
    }
}
