package com.veil.testfeed

import org.junit.Assert.assertEquals
import org.junit.Test

class FeedJsonTest {
    @Test
    fun frameLineIsExact() {
        val visible =
            listOf(
                VisibleItem("item-000", "clean", IntRect(0, -300, 1080, 900)),
                VisibleItem("item-001", "cat", IntRect(0, 608, 1080, 900))
            )
        val expected =
            "{\"type\":\"frame\",\"tMs\":1234,\"scrollY\":300,\"visible\":[" +
                "{\"itemId\":\"item-000\",\"kind\":\"clean\",\"rect\":{\"x\":0,\"y\":-300,\"w\":1080,\"h\":900}}," +
                "{\"itemId\":\"item-001\",\"kind\":\"cat\",\"rect\":{\"x\":0,\"y\":608,\"w\":1080,\"h\":900}}]}"
        assertEquals(expected, FeedJson.frame(1234L, 300, visible))
    }

    @Test
    fun sessionLineIsExact() {
        val expected =
            "{\"type\":\"session\",\"v\":1,\"tMs\":5,\"screenWidthPx\":1440,\"screenHeightPx\":3168," +
                "\"densityDpi\":510,\"viewport\":{\"x\":0,\"y\":100,\"w\":1440,\"h\":3000}," +
                "\"items\":[{\"itemId\":\"item-000\",\"kind\":\"clean\",\"contentY\":0,\"h\":900}]}"
        val items = listOf(ItemLayout("item-000", "clean", 0, 900))
        assertEquals(expected, FeedJson.session(5L, 1440, 3168, 510, IntRect(0, 100, 1440, 3000), items))
    }

    @Test
    fun tapAndPauseLines() {
        assertEquals(
            "{\"type\":\"tap\",\"tMs\":7,\"x\":10,\"y\":20,\"itemId\":\"item-004\"}",
            FeedJson.tap(7L, 10, 20, "item-004")
        )
        assertEquals("{\"type\":\"tap\",\"tMs\":7,\"x\":10,\"y\":20}", FeedJson.tap(7L, 10, 20, null))
        assertEquals("{\"type\":\"pause\",\"tMs\":9}", FeedJson.pause(9L))
    }
}
