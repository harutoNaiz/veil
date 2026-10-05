package com.veil.guard.overlay.glue

import com.veil.guard.overlay.Px
import com.veil.guard.signals.PxRect
import com.veil.guard.signals.ScrollDelta
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class GluedBoxTest {
    private val rect = PxRect(0, 0, 1000, 2000)

    @Test fun followsContentSign() {
        val b = GluedBox(Px(100, 500, 200, 200))
        assertTrue(b.apply(ScrollDelta(0, -120, "list", rect), 1))
        assertEquals(380, b.position().y)
    }

    @Test fun accumulatesOver100Events() {
        val b = GluedBox(Px(100, 1500, 200, 200))
        repeat(100) { b.apply(ScrollDelta(3, -10, "list", rect), it.toLong()) }
        assertEquals(500, b.position().y)
        assertEquals(400, b.position().x)
    }

    @Test fun unknownContainerCountsMismatch() {
        val b = GluedBox(Px(100, 500, 200, 200))
        assertFalse(b.apply(ScrollDelta(0, -50, null, null), 1))
        assertEquals(1, b.mismatch)
        assertEquals(500, b.position().y)
    }

    @Test fun containerNotUnderBoxIgnored() {
        val b = GluedBox(Px(100, 500, 200, 200))
        assertFalse(b.apply(ScrollDelta(0, -50, "nested", PxRect(0, 1200, 1000, 500)), 1))
        assertEquals(500, b.position().y)
    }

    @Test fun resetRestoresStart() {
        val b = GluedBox(Px(100, 500, 200, 200))
        b.apply(ScrollDelta(0, -50, "list", rect), 1)
        b.reset()
        assertEquals(Px(100, 500, 200, 200), b.position())
    }
}
