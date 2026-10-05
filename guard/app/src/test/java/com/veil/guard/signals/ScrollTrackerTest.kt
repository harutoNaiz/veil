package com.veil.guard.signals

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class ScrollTrackerTest {
    private fun raw(key: String? = "a", dY: Int = 0, sY: Int = -1, h: Int = 1000, win: Int = 1) = RawEvent(
        type = 4096,
        tMs = 0,
        packageName = "p",
        className = "c",
        windowId = win,
        sourceKey = key,
        sourceRect = PxRect(0, 0, 1000, h),
        scrollDeltaX = 0,
        scrollDeltaY = dY,
        scrollX = -1,
        scrollY = sY,
        maxScrollX = -1,
        maxScrollY = -1,
        contentChangeTypes = 0
    )

    @Test fun positiveDeltaGivesNegativeContentDy() {
        assertEquals(-120, ScrollTracker().onScroll(raw(dY = 120))?.dy)
        assertEquals(80, ScrollTracker().onScroll(raw(dY = -80))?.dy)
    }

    @Test fun absoluteSequenceFirstEventStoresOnly() {
        val t = ScrollTracker()
        assertNull(t.onScroll(raw(sY = 100)))
        assertEquals(-50, t.onScroll(raw(sY = 150))?.dy)
        assertEquals(30, t.onScroll(raw(sY = 120))?.dy)
        assertNull(t.onScroll(raw(sY = 120)))
    }

    @Test fun interleavedContainers() {
        val t = ScrollTracker()
        assertNull(t.onScroll(raw(key = "a", sY = 0)))
        assertNull(t.onScroll(raw(key = "b", sY = 500)))
        assertEquals(-10, t.onScroll(raw(key = "a", sY = 10))?.dy)
        assertEquals(-20, t.onScroll(raw(key = "b", sY = 520))?.dy)
        assertNull(t.onScroll(raw(key = "a", sY = 10, win = 2)))
    }

    @Test fun resetClears() {
        val t = ScrollTracker()
        t.onScroll(raw(sY = 0))
        t.reset()
        assertNull(t.onScroll(raw(sY = 100)))
    }

    @Test fun jumpGuard() {
        val t = ScrollTracker()
        t.onScroll(raw(sY = 0))
        assertNull(t.onScroll(raw(sY = 5000)))
        assertEquals(-10, t.onScroll(raw(sY = 5010))?.dy)
    }

    @Test fun indexOnlyReturnsNull() {
        assertNull(ScrollTracker().onScroll(raw()))
    }
}
