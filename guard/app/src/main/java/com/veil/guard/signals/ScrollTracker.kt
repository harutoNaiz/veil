package com.veil.guard.signals

import kotlin.math.abs

/** Turns raw scroll events into content-moved deltas (screen px). */
class ScrollTracker : ScrollNormaliser {
    private val lastX = HashMap<String, Int>()
    private val lastY = HashMap<String, Int>()

    override fun onScroll(raw: RawEvent): ScrollDelta? {
        val key = "${raw.windowId}/${raw.sourceKey ?: raw.className}"
        var dx = 0
        var dy = 0
        if (raw.scrollDeltaX != 0 || raw.scrollDeltaY != 0) {
            dx = -raw.scrollDeltaX
            dy = -raw.scrollDeltaY
        } else if (raw.scrollX >= 0 || raw.scrollY >= 0) {
            dx = absDiff(lastX, key, raw.scrollX, raw.sourceRect?.w ?: 0)
            dy = absDiff(lastY, key, raw.scrollY, raw.sourceRect?.h ?: 0)
        }
        if (dx == 0 && dy == 0) return null
        return ScrollDelta(dx, dy, raw.sourceKey, raw.sourceRect)
    }

    private fun absDiff(store: MutableMap<String, Int>, key: String, cur: Int, size: Int): Int {
        if (cur < 0) return 0
        val last = store.put(key, cur) ?: return 0
        val diff = cur - last
        if (size > 0 && abs(diff) > 4 * size) return 0
        return -diff
    }

    override fun reset() {
        lastX.clear()
        lastY.clear()
    }
}
