package com.veil.conductor.video

import com.veil.brain.contract.Finding
import com.veil.brain.contract.Rect

/** Turns partial hits inside a playing-video region into one sticky whole-region cover. Pure. */
class StickyVideo {
    private class Sticky(var rect: Rect, val conceptId: String, val layer: Int, var frameId: Int, var lastHitMs: Long) {
        var clean = 0
        var lostSince: Long? = null
        var hit = false
    }

    private val stickies = ArrayList<Sticky>()

    fun activeRects(): List<Rect> = stickies.map { it.rect }

    fun apply(found: List<Finding>, regions: List<Rect>, lookId: Int, tMs: Long): List<Finding> {
        for (s in stickies) {
            s.hit = false
            val m = regions.maxByOrNull { iou(it, s.rect) }
            if (m != null && iou(m, s.rect) >= 0.3) {
                // Grow only: a walking animal moves the changing part around inside a still player.
                s.rect = grow(s.rect, m)
                s.lostSince = null
            } else if (regions.none { inter(s.rect, it) > 0 }) {
                // The video moved (full player <-> mini player, new page): follow it to a playing area no other
                // cover holds, rather than leave a cover on whatever is now at the old place.
                val moved = regions.filter { r -> stickies.none { it !== s && inter(it.rect, r) > 0 } }
                    .maxByOrNull { it.w.toLong() * it.h }
                if (moved != null) {
                    s.rect = moved
                    s.lostSince = null
                } else if (s.lostSince == null) {
                    s.lostSince = tMs
                }
            }
        }
        stickies.removeAll {
            val l = it.lostSince
            l != null && tMs - l > LOST_MS
        }
        val out = ArrayList<Finding>()
        for (f in found) {
            if (f.decision != "hide" && f.decision != "nearMiss") {
                out.add(f)
                continue
            }
            var s = stickies.firstOrNull { hits(f.rect, it.rect) }
            if (s == null && f.decision == "hide") {
                val r = regions.firstOrNull { hits(f.rect, it) }
                if (r != null) {
                    s = Sticky(grow(r, f.rect), f.conceptId, f.layer, f.frameId, tMs)
                    stickies.add(s)
                }
            }
            if (s == null) {
                out.add(f)
                continue
            }
            s.hit = true
            s.lastHitMs = tMs
            if (f.decision == "hide") s.rect = grow(s.rect, f.rect) // hides are snapped to the whole picture
            s.frameId = f.frameId
            if (f.decision == "nearMiss") out.add(f)
        }
        val it = stickies.iterator()
        var n = 0
        while (it.hasNext()) {
            val s = it.next()
            if (s.hit) {
                s.clean = 0
            } else {
                s.clean++
                if (s.clean >= CLEAN_LOOKS && tMs - s.lastHitMs >= CLEAN_MS) {
                    it.remove()
                    continue
                }
            }
            out.add(
                Finding(
                    "vid-$lookId-${n++}", s.frameId, lookId, tMs, s.conceptId, s.layer, "hide", 1.0, s.rect,
                    "object", "video"
                )
            )
        }
        return out
    }

    /** Union of the two, unless that is more than twice the larger (then the newer one: it moved). */
    private fun grow(a: Rect, b: Rect): Rect {
        val x0 = minOf(a.x, b.x)
        val y0 = minOf(a.y, b.y)
        val u = Rect(x0, y0, maxOf(a.x + a.w, b.x + b.w) - x0, maxOf(a.y + a.h, b.y + b.h) - y0)
        val big = maxOf(a.w.toLong() * a.h, b.w.toLong() * b.h)
        return if (u.w.toLong() * u.h > 2 * big) b else u
    }

    private fun hits(f: Rect, r: Rect): Boolean {
        val cx = f.x + f.w / 2
        val cy = f.y + f.h / 2
        if (cx >= r.x && cx < r.x + r.w && cy >= r.y && cy < r.y + r.h) return true
        val area = f.w.toLong() * f.h
        return area > 0 && inter(f, r) >= 0.3 * area
    }

    private fun inter(a: Rect, b: Rect): Long {
        val w = minOf(a.x + a.w, b.x + b.w) - maxOf(a.x, b.x)
        val h = minOf(a.y + a.h, b.y + b.h) - maxOf(a.y, b.y)
        return if (w > 0 && h > 0) w.toLong() * h else 0L
    }

    private fun iou(a: Rect, b: Rect): Double {
        val i = inter(a, b).toDouble()
        val u = a.w.toLong() * a.h + b.w.toLong() * b.h - i
        return if (u <= 0) 0.0 else i / u
    }

    private companion object {
        const val LOST_MS = 600L // video moved (mini player, new page): drop the old cover fast
        const val CLEAN_LOOKS = 4
        const val CLEAN_MS = 3000L
    }
}
