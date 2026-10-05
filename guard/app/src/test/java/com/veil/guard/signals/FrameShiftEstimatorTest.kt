package com.veil.guard.signals

import kotlin.math.abs
import kotlin.random.Random
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class FrameShiftEstimatorTest {
    private val h = 400
    private val base = Random(7).let { r -> IntArray(h + 200) { r.nextInt(256) } }

    private fun frame(offset: Int) = IntArray(h) { base[it + 100 + offset] }

    @Test fun detectsShifts() {
        for (s in listOf(-40, -7, 1, 13, 60)) {
            val got = FrameShiftEstimator.estimate(frame(0), frame(-s), 100, h, 100)
            assertNotNull(got)
            assertTrue(abs(got!! - s) <= 1)
        }
    }

    @Test fun identicalIsNull() {
        assertNull(FrameShiftEstimator.estimate(frame(0), frame(0), 100, h, 100))
    }

    @Test fun unrelatedIsNull() {
        val other = Random(99).let { r -> IntArray(h) { r.nextInt(256) } }
        assertNull(FrameShiftEstimator.estimate(frame(0), other, 100, h, 100))
    }
}
