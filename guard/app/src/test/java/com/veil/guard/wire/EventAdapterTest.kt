package com.veil.guard.wire

import com.veil.guard.signals.ContentChanged
import com.veil.guard.signals.NodesSnapshot
import com.veil.guard.signals.PxRect
import com.veil.guard.signals.ScreenOff
import com.veil.guard.signals.ScreenOn
import com.veil.guard.signals.Scrolled
import com.veil.guard.signals.SnapNode
import com.veil.guard.signals.WindowChanged
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class EventAdapterTest {
    @Test
    fun maps() {
        val s = EventAdapter.toBrain(Scrolled(1, 10, "p", 3, -4))!!
        assertEquals(listOf("scrolled", 10L, 3, -4, "p"), listOf(s.type, s.tMs, s.dx, s.dy, s.packageName))
        assertEquals("windowChanged", EventAdapter.toBrain(WindowChanged(1, 1, "p"))!!.type)
        assertEquals("contentChanged", EventAdapter.toBrain(ContentChanged(1, 1, "p"))!!.type)
        assertEquals("screenOff", EventAdapter.toBrain(ScreenOff(1, 1))!!.type)
        assertEquals("screenOn", EventAdapter.toBrain(ScreenOn(1, 1))!!.type)
        assertNull(EventAdapter.toBrain(NodesSnapshot(1, 1, null, emptyList(), false, 0)))
    }

    @Test
    fun node() {
        val n = EventAdapter.toLayout(SnapNode("image", PxRect(1, 2, 3, 4), text = "t"))
        assertEquals("image", n.kind)
        assertEquals(listOf(1, 2, 3, 4), listOf(n.rect.x, n.rect.y, n.rect.w, n.rect.h))
        assertEquals("t", n.text)
    }
}
