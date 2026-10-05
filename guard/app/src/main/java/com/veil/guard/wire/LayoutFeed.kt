package com.veil.guard.wire

import android.os.SystemClock
import com.veil.conductor.LayoutNode
import com.veil.guard.signals.SignalsHub

class LayoutFeed(private val now: () -> Long = SystemClock::uptimeMillis) {
    private var cached: List<LayoutNode> = emptyList()
    private var at = Long.MIN_VALUE / 2

    @Synchronized
    fun latest(): List<LayoutNode> {
        val t = now()
        if (t - at > 250) {
            runCatching {
                SignalsHub.snapshotter?.snapshot()?.let { s ->
                    cached = s.nodes.map(EventAdapter::toLayout)
                    at = t
                }
            }
        }
        return cached
    }
}
