package com.veil.guard.overlay.touch

import kotlin.math.hypot

data class TimedPoint(val x: Int, val y: Int, val tMs: Long)

sealed interface TouchResult {
    data class Tap(val x: Int, val y: Int) : TouchResult

    data class Drag(val points: List<TimedPoint>) : TouchResult

    data class LongPress(val x: Int, val y: Int, val tMs: Long) : TouchResult
}

/** Pure down/move/up/cancel classifier. Drive the hold timer with [tick]. */
class LongPressDetector(private val longMs: Long = 500, private val slopPx: Int = 24) {
    private val points = ArrayList<TimedPoint>()
    private var moved = false
    private var fired = false

    fun down(x: Int, y: Int, tMs: Long) {
        points.clear()
        points.add(TimedPoint(x, y, tMs))
        moved = false
        fired = false
    }

    fun move(x: Int, y: Int, tMs: Long) {
        if (points.isEmpty()) return
        points.add(TimedPoint(x, y, tMs))
        val s = points.first()
        if (hypot((x - s.x).toDouble(), (y - s.y).toDouble()) > slopPx) moved = true
    }

    /** Returns LongPress once, when the finger has held still for longMs. */
    fun tick(nowMs: Long): TouchResult.LongPress? {
        if (points.isEmpty() || moved || fired) return null
        val s = points.first()
        if (nowMs - s.tMs < longMs) return null
        fired = true
        return TouchResult.LongPress(s.x, s.y, nowMs)
    }

    fun up(x: Int, y: Int, tMs: Long): TouchResult? {
        if (points.isEmpty()) return null
        move(x, y, tMs)
        val pts = points.toList()
        points.clear()
        return when {
            fired -> null
            moved -> TouchResult.Drag(pts)
            tMs - pts.first().tMs >= longMs -> TouchResult.LongPress(pts.first().x, pts.first().y, tMs)
            else -> TouchResult.Tap(pts.first().x, pts.first().y)
        }
    }

    fun cancel() {
        points.clear()
        fired = false
        moved = false
    }
}
