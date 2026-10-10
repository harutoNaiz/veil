package com.veil.guard.capture.source

import com.veil.guard.capture.CoverMath
import com.veil.guard.capture.PxRect
import org.junit.Assert.assertEquals
import org.junit.Test

class CoverMathTest {
    private fun px(x: Int, y: Int, w: Int, h: Int) = PxRect(x, y, w, h)

    @Test
    fun fullScreenIsOne() = assertEquals(1.0, CoverMath.fraction(listOf(px(0, 0, 1440, 3168)), 1440, 3168), 1e-9)

    @Test
    fun overlapCountedOnce() {
        val a = px(0, 0, 720, 3168)
        assertEquals(0.5, CoverMath.fraction(listOf(a, a, px(0, 0, 720, 1584)), 1440, 3168), 1e-9)
    }

    @Test
    fun emptyIsZero() = assertEquals(0.0, CoverMath.fraction(emptyList(), 1440, 3168), 0.0)
}
