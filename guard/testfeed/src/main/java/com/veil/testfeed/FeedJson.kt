package com.veil.testfeed

import java.util.Locale

/** One JSON object per call, built by hand (no org.json, so it can be unit-tested on the JVM). */
object FeedJson {
    private const val VERSION = 1

    fun session(
        tMs: Long,
        screenW: Int,
        screenH: Int,
        densityDpi: Int,
        viewport: IntRect,
        items: List<ItemLayout>
    ): String = buildString {
        append("{\"type\":\"session\",\"v\":").append(VERSION)
        append(",\"tMs\":").append(tMs)
        append(",\"screenWidthPx\":").append(screenW)
        append(",\"screenHeightPx\":").append(screenH)
        append(",\"densityDpi\":").append(densityDpi)
        append(",\"viewport\":").append(rect(viewport))
        append(",\"items\":[")
        items.forEachIndexed { index, item ->
            if (index > 0) append(',')
            append("{\"itemId\":").append(quote(item.itemId))
            append(",\"kind\":").append(quote(item.kind))
            append(",\"contentY\":").append(item.contentY)
            append(",\"h\":").append(item.h).append('}')
        }
        append("]}")
    }

    fun frame(tMs: Long, scrollY: Int, visible: List<VisibleItem>): String = buildString {
        append("{\"type\":\"frame\",\"tMs\":").append(tMs)
        append(",\"scrollY\":").append(scrollY)
        append(",\"visible\":[")
        visible.forEachIndexed { index, item ->
            if (index > 0) append(',')
            append("{\"itemId\":").append(quote(item.itemId))
            append(",\"kind\":").append(quote(item.kind))
            append(",\"rect\":").append(rect(item.rect)).append('}')
        }
        append("]}")
    }

    /** [itemId] is left out when the tap misses every item. */
    fun tap(tMs: Long, x: Int, y: Int, itemId: String?): String = buildString {
        append("{\"type\":\"tap\",\"tMs\":").append(tMs)
        append(",\"x\":").append(x)
        append(",\"y\":").append(y)
        if (itemId != null) append(",\"itemId\":").append(quote(itemId))
        append('}')
    }

    fun pause(tMs: Long): String = "{\"type\":\"pause\",\"tMs\":$tMs}"

    private fun rect(r: IntRect): String = "{\"x\":${r.x},\"y\":${r.y},\"w\":${r.w},\"h\":${r.h}}"

    private fun quote(value: String): String = buildString {
        append('"')
        for (c in value) {
            when {
                c == '"' -> append("\\\"")
                c == '\\' -> append("\\\\")
                c < ' ' -> append(String.format(Locale.ROOT, "\\u%04x", c.code))
                else -> append(c)
            }
        }
        append('"')
    }
}
