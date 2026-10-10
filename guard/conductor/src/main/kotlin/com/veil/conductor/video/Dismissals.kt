package com.veil.conductor.video

import com.veil.brain.contract.Finding
import com.veil.brain.contract.Rect

/**
 * "Continue" (adult mode): the viewer saw the warning and chose to watch. From then on nothing is covered inside
 * that area. A dismissed video follows the video if it moves and lasts until the video has not played for
 * [videoGoneMs] (it ended, the viewer left, or a new video started after a pause): the next video warns again.
 * A dismissed still picture lasts while it is still found on screen. Pure.
 */
class Dismissals(private val videoGoneMs: Long = 8000, private val stillGoneMs: Long = 2500) {
    private class D(var rect: Rect, val video: Boolean, var lastSeen: Long, var sig: IntArray? = null)

    private val list = ArrayList<D>()

    fun add(r: Rect, video: Boolean, tMs: Long, frame: com.veil.conductor.Frame? = null) {
        list.add(D(r, video, tMs, frame?.let { StillHold.signature(it, r) }))
    }

    fun active(): List<Rect> = list.map { it.rect }

    fun apply(
        found: List<Finding>,
        videos: List<Rect>,
        tMs: Long,
        frame: com.veil.conductor.Frame? = null
    ): List<Finding> {
        // Expire first: a video that comes back after a long gap is a new viewing and warns again.
        list.removeAll { tMs - it.lastSeen > if (it.video) videoGoneMs else stillGoneMs }
        for (d in list) {
            if (d.video) {
                val v = videos.filter { inter(it, d.rect) > 0 }.maxByOrNull { inter(it, d.rect) }
                    ?: videos.singleOrNull() // moved (mini player <-> full player): the one playing video
                if (v != null) {
                    d.rect = v
                    d.lastSeen = tMs
                }
            } else if (d.sig != null && frame != null) {
                // A still picture stays dismissed while it is unchanged (detection flips look to look).
                val now = StillHold.signature(frame, d.rect)
                if (now != null && StillHold.diff(now, d.sig!!) <= SAME_PICTURE) d.lastSeen = tMs
            } else {
                val f = found.filter { it.decision != "leave" && frac(it.rect, d.rect) >= 0.3 }
                    .maxByOrNull { inter(it.rect, d.rect) }
                if (f != null) {
                    d.rect = f.rect
                    d.lastSeen = tMs
                }
            }
        }
        if (list.isEmpty()) return found
        return found.filter { f -> list.none { d -> inter(f.rect, d.rect) >= 0.5 * minOf(area(f.rect), area(d.rect)) } }
    }

    fun clear() = list.clear()

    private fun inter(a: Rect, b: Rect): Long {
        val w = minOf(a.x + a.w, b.x + b.w) - maxOf(a.x, b.x)
        val h = minOf(a.y + a.h, b.y + b.h) - maxOf(a.y, b.y)
        return if (w > 0 && h > 0) w.toLong() * h else 0L
    }

    private fun area(r: Rect) = r.w.toLong() * r.h

    private companion object {
        const val SAME_PICTURE = 20
    }

    /** Share of [a] that lies inside [b]. */
    private fun frac(a: Rect, b: Rect): Double {
        val area = a.w.toLong() * a.h
        return if (area <= 0) 0.0 else inter(a, b).toDouble() / area
    }
}
