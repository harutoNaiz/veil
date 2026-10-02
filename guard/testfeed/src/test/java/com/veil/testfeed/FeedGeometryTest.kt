package com.veil.testfeed

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class FeedGeometryTest {
    // Three items of 100 px with a 10 px gap: [0,100) [110,210) [220,320).
    private val items =
        listOf(
            ItemLayout("item-000", "clean", 0, 100),
            ItemLayout("item-001", "cat", 110, 100),
            ItemLayout("item-002", "clean", 220, 100)
        )
    private val viewport = IntRect(0, 50, 1000, 150)

    @Test
    fun atTopOfFeed() {
        val visible = FeedGeometry.visible(items, 0, viewport)
        assertEquals(listOf("item-000", "item-001"), visible.map { it.itemId })
        assertEquals(IntRect(0, 50, 1000, 100), visible[0].rect)
        assertEquals(IntRect(0, 160, 1000, 100), visible[1].rect)
    }

    @Test
    fun midScrollPartialOverlap() {
        // Viewport shows content [90, 240): item-000 shows its last 10 px, item-002 its first 20 px.
        val visible = FeedGeometry.visible(items, 90, viewport)
        assertEquals(listOf("item-000", "item-001", "item-002"), visible.map { it.itemId })
        assertEquals(-40, visible[0].rect.y)
        assertEquals(70, visible[1].rect.y)
        assertEquals(180, visible[2].rect.y)
        assertEquals("cat", visible[1].kind)
    }

    @Test
    fun pastTheEnd() {
        assertEquals(emptyList<VisibleItem>(), FeedGeometry.visible(items, 320, viewport))
        assertEquals(emptyList<VisibleItem>(), FeedGeometry.visible(items, 5000, viewport))
    }

    @Test
    fun edgesAreHalfOpen() {
        // Content [100, 250): item-000 ends exactly at 100 so it is out; item-002 starts at 220 so it is in.
        val visible = FeedGeometry.visible(items, 100, viewport)
        assertEquals(listOf("item-001", "item-002"), visible.map { it.itemId })
    }

    @Test
    fun hitTestFindsTheItemOrNull() {
        assertEquals("item-000", FeedGeometry.hitTest(items, 0, viewport, 500, 60))
        assertEquals("item-001", FeedGeometry.hitTest(items, 0, viewport, 500, 170))
        assertNull(FeedGeometry.hitTest(items, 0, viewport, 500, 155)) // the gap between items
        assertNull(FeedGeometry.hitTest(items, 0, viewport, 500, 10)) // above the viewport
        assertNull(FeedGeometry.hitTest(items, 0, viewport, 1000, 60)) // right of the viewport
    }
}
