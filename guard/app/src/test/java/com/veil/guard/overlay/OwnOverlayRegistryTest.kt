package com.veil.guard.overlay

import com.veil.guard.overlay.self.OwnOverlayRegistry
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class OwnOverlayRegistryTest {
    private val a = Px(10, 20, 100, 50)
    private val b = Px(0, 0, 5, 5)

    @Test fun lookupBeforeBetweenAfter() {
        val reg = OwnOverlayRegistry()
        reg.onDrawn(OwnOverlaySample(100, listOf(a)))
        reg.onDrawn(OwnOverlaySample(200, listOf(b)))
        assertTrue(reg.at(50).isEmpty())
        assertEquals(listOf(a), reg.at(150))
        assertEquals(listOf(b), reg.at(999))
    }

    @Test fun capacityEvictsOldest() {
        val reg = OwnOverlayRegistry(capacity = 2)
        for (t in 1L..3L) reg.onDrawn(OwnOverlaySample(t, listOf(a)))
        assertTrue(reg.at(1).isEmpty())
    }

    @Test fun scalingRoundsOutwardWithin2px() {
        val r = OwnOverlayRegistry.scaled(listOf(Px(73, 1021, 1295, 641)), 1440, 3168, 360, 792)[0]
        assertTrue(r.x * 4 <= 73 && (r.x + r.w) * 4 >= 73 + 1295)
        assertTrue(r.y * 4 <= 1021 && (r.y + r.h) * 4 >= 1021 + 641)
        assertTrue(r.w <= 1295 / 4 + 2 && r.h <= 641 / 4 + 2)
    }
}
