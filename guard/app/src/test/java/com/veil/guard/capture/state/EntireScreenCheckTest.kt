package com.veil.guard.capture.state

import com.veil.guard.capture.FrameSize
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class EntireScreenCheckTest {
    @Test
    fun withinTolerancePasses() {
        // 1% off each dimension, tol default 0.02.
        assertTrue(
            EntireScreenCheck.isEntireScreen(FrameSize(1069, 2376), FrameSize(1080, 2400))
        )
    }

    @Test
    fun outsideToleranceFails() {
        assertFalse(
            EntireScreenCheck.isEntireScreen(FrameSize(900, 2000), FrameSize(1080, 2400))
        )
    }
}
