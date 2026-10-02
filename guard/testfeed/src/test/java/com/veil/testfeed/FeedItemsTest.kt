package com.veil.testfeed

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class FeedItemsTest {
    @Test
    fun feedHasSixtyItemsWithUniqueIds() {
        val feed = FeedItems.defaultFeed()
        assertEquals(60, feed.size)
        assertEquals(60, feed.map { it.id }.toSet().size)
        assertEquals("item-000", feed.first().id)
        assertEquals("item-059", feed.last().id)
    }

    @Test
    fun feedIsDeterministic() {
        assertEquals(FeedItems.defaultFeed(), FeedItems.defaultFeed())
    }

    @Test
    fun itemSixIsARulerOf480Dp() {
        val item = FeedItems.defaultFeed()[6]
        assertEquals("item-006", item.id)
        assertEquals("ruler", item.kind)
        assertEquals(480, item.heightDp)
        assertEquals("#006 ruler", item.label)
    }

    @Test
    fun otherItemsAre320DpAndRepostsPointAtItemOne() {
        val feed = FeedItems.defaultFeed()
        assertTrue(feed.filter { it.kind != "ruler" }.all { it.heightDp == 320 })
        assertEquals("#007 repost of item-001", feed[7].label)
        assertEquals("#003 spider", feed[3].label)
        assertEquals(0xFFB39DDB.toInt(), feed[3].color)
    }
}
