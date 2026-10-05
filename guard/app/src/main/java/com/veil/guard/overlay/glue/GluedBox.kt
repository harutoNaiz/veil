package com.veil.guard.overlay.glue

import com.veil.guard.overlay.Px
import com.veil.guard.signals.ScrollDelta

/** Pure: a box that follows content moved by scroll deltas. */
class GluedBox(private val start: Px) {
    private var box = start
    var mismatch = 0
        private set
    var applied = 0
        private set
    var lastMs = 0L
        private set

    fun apply(d: ScrollDelta, nowMs: Long): Boolean {
        val r = d.containerRect
        if (d.containerId == null && r == null) {
            mismatch++
            return false
        }
        if (r != null) {
            val cx = box.x + box.w / 2
            val cy = box.y + box.h / 2
            if (cx < r.x || cx >= r.x + r.w || cy < r.y || cy >= r.y + r.h) return false
        }
        box = box.copy(x = box.x + d.dx, y = box.y + d.dy)
        applied++
        lastMs = nowMs
        return true
    }

    fun position(): Px = box

    fun reset() {
        box = start
        mismatch = 0
        applied = 0
    }
}
