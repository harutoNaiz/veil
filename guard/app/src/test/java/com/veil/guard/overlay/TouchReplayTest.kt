package com.veil.guard.overlay

import com.veil.guard.overlay.touch.TimedPoint
import com.veil.guard.overlay.touch.TouchReplay
import com.veil.guard.overlay.touch.TouchResult
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class TouchReplayTest {
    @Test fun tapStroke() {
        val s = TouchReplay.toStrokes(TouchResult.Tap(7, 8)).single()
        assertEquals(listOf(7 to 8), s.path)
        assertEquals(TouchReplay.TAP_MS, s.durationMs)
    }

    @Test fun dragKeepsPathAndDuration() {
        val pts = listOf(TimedPoint(0, 0, 1000), TimedPoint(0, 40, 1100), TimedPoint(0, 90, 1180))
        val s = TouchReplay.toStrokes(TouchResult.Drag(pts)).single()
        assertEquals(listOf(0 to 0, 0 to 40, 0 to 90), s.path)
        assertEquals(180L, s.durationMs)
        assertEquals(0L, s.startMs)
    }

    @Test fun longPressNotReplayed() {
        assertTrue(TouchReplay.toStrokes(TouchResult.LongPress(1, 1, 0)).isEmpty())
    }
}
