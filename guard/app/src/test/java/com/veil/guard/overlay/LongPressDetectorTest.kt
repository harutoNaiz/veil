package com.veil.guard.overlay

import com.veil.guard.overlay.touch.LongPressDetector
import com.veil.guard.overlay.touch.TouchResult
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class LongPressDetectorTest {
    @Test fun tap() {
        val d = LongPressDetector()
        d.down(5, 6, 0)
        assertEquals(TouchResult.Tap(5, 6), d.up(5, 6, 100))
    }

    @Test fun dragPastSlop() {
        val d = LongPressDetector(slopPx = 10)
        d.down(0, 0, 0)
        d.move(0, 50, 50)
        assertNull(d.tick(600))
        assertTrue(d.up(0, 100, 120) is TouchResult.Drag)
    }

    @Test fun longPressAt500() {
        val d = LongPressDetector()
        d.down(1, 2, 1000)
        assertNull(d.tick(1499))
        assertEquals(TouchResult.LongPress(1, 2, 1500), d.tick(1500))
        assertNull(d.up(1, 2, 1700))
    }

    @Test fun cancelDropsGesture() {
        val d = LongPressDetector()
        d.down(1, 2, 0)
        d.cancel()
        assertNull(d.tick(900))
        assertNull(d.up(1, 2, 950))
    }
}
