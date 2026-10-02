package com.veil.testfeed

data class IntRect(val x: Int, val y: Int, val w: Int, val h: Int)

/** Where an item sits inside the scroll content, in px. [contentY] counts from the top of the content. */
data class ItemLayout(val itemId: String, val kind: String, val contentY: Int, val h: Int)

/** An item that is at least partly on screen. [rect] is in screen px and is not clipped to the viewport. */
data class VisibleItem(val itemId: String, val kind: String, val rect: IntRect)

object FeedGeometry {
    /**
     * Items whose [contentY, contentY+h) intersects [scrollY, scrollY+viewport.h);
     * rect.y = viewport.y + contentY - scrollY, rect.x = viewport.x, rect.w = viewport.w, rect.h = h.
     * Order = feed order.
     */
    fun visible(items: List<ItemLayout>, scrollY: Int, viewport: IntRect): List<VisibleItem> {
        val bottom = scrollY + viewport.h
        return items
            .filter { it.contentY < bottom && it.contentY + it.h > scrollY }
            .map {
                VisibleItem(
                    itemId = it.itemId,
                    kind = it.kind,
                    rect = IntRect(viewport.x, viewport.y + it.contentY - scrollY, viewport.w, it.h)
                )
            }
    }

    /** The id of the item under the screen point ([x], [y]), or null when the point misses every item. */
    fun hitTest(items: List<ItemLayout>, scrollY: Int, viewport: IntRect, x: Int, y: Int): String? {
        if (x < viewport.x || x >= viewport.x + viewport.w) return null
        if (y < viewport.y || y >= viewport.y + viewport.h) return null
        val contentY = y - viewport.y + scrollY
        return items.firstOrNull { contentY >= it.contentY && contentY < it.contentY + it.h }?.itemId
    }
}
