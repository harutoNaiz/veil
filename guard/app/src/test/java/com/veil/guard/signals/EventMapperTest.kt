package com.veil.guard.signals

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class EventMapperTest {
    private class FakeScroll(var out: ScrollDelta? = null) : ScrollNormaliser {
        var resets = 0

        override fun onScroll(raw: RawEvent) = out

        override fun reset() {
            resets++
        }
    }

    private fun raw(type: Int, pkg: String? = "com.app.x", changes: Int = 0, rect: PxRect? = null) =
        RawEvent(type, 1234, pkg, "cls", 7, null, rect, 0, 0, -1, -1, -1, -1, changes)

    private var id = 0L
    private val next = { id++ }

    @Test fun windowState() {
        val e = EventMapper(FakeScroll()).map(raw(EventMapper.TYPE_WINDOW_STATE_CHANGED), next) as WindowChanged
        assertEquals("com.app.x", e.packageName)
        assertEquals("cls", e.className)
        assertEquals(7, e.windowId)
        assertEquals(1234L, e.tMs)
    }

    @Test fun ownOverlayWindowStateDropped() {
        val m = EventMapper(FakeScroll(), "com.veil.guard") { it == "com.veil.guard.MainActivity" }
        val overlay = raw(EventMapper.TYPE_WINDOW_STATE_CHANGED, pkg = "com.veil.guard")
        assertNull(m.map(overlay, next))
    }

    @Test fun ownActivityWindowStateKept() {
        val m = EventMapper(FakeScroll(), "com.veil.guard") { it == "com.veil.guard.MainActivity" }
        val r = raw(EventMapper.TYPE_WINDOW_STATE_CHANGED, pkg = "com.veil.guard")
        val e = m.map(r.copy(className = "com.veil.guard.MainActivity"), next) as WindowChanged
        assertEquals("com.veil.guard", e.packageName)
    }

    @Test fun windowStateNullPackageDropped() {
        assertNull(EventMapper(FakeScroll()).map(raw(EventMapper.TYPE_WINDOW_STATE_CHANGED, pkg = null), next))
    }

    @Test fun contentChanged() {
        val r = PxRect(1, 2, 3, 4)
        val e = EventMapper(
            FakeScroll()
        ).map(raw(EventMapper.TYPE_WINDOW_CONTENT_CHANGED, null, 3, r), next) as ContentChanged
        assertNull(e.packageName)
        assertEquals(listOf("subtree", "text"), e.changeTypes)
        assertEquals(r, e.rect)
    }

    @Test fun scrollUsesTracker() {
        val fs = FakeScroll()
        val m = EventMapper(fs)
        assertNull(m.map(raw(EventMapper.TYPE_VIEW_SCROLLED), next))
        fs.out = ScrollDelta(0, -50, "id", PxRect(0, 0, 10, 10))
        val e = m.map(raw(EventMapper.TYPE_VIEW_SCROLLED), next) as Scrolled
        assertEquals(-50, e.dy)
        assertEquals("id", e.containerId)
    }

    @Test fun windowsChangedResets() {
        val fs = FakeScroll()
        assertNull(EventMapper(fs).map(raw(EventMapper.TYPE_WINDOWS_CHANGED), next))
        assertEquals(1, fs.resets)
    }

    @Test fun unknownIgnoredAndIdsAdvance() {
        val m = EventMapper(FakeScroll())
        assertNull(m.map(raw(0x1), next))
        m.map(raw(EventMapper.TYPE_WINDOW_STATE_CHANGED), next)
        m.map(raw(EventMapper.TYPE_WINDOW_STATE_CHANGED), next)
        assertEquals(2L, id)
    }
}
