package com.veil.conductor.video

import com.veil.brain.contract.Finding
import com.veil.brain.contract.Rect
import com.veil.conductor.Frame

/**
 * Keeps a cover on a still picture for as long as the picture under it is unchanged, even when a later look is
 * unsure (hide one look, near-miss the next): that flip-flop made covers blink on and off. A cover is released as
 * soon as the pixels under it change (scrolled away, new page), so it never sits on content that replaced it.
 * Pure; [frame] must be a shot without our own covers.
 */
class StillHold(private val maxDiff: Int = 14, private val maxAgeMs: Long = 120_000) {
    private class Held(var rect: Rect, var f: Finding, var sig: IntArray, val since: Long)

    private val held = ArrayList<Held>()

    fun apply(found: List<Finding>, frame: Frame?, lookId: Int, tMs: Long): List<Finding> {
        val out = ArrayList(found)
        val hides = found.filter { it.decision == "hide" && it.lane != "hold" }
        val refreshed = HashSet<Held>()
        for (f in hides) {
            val sig = frame?.let { signature(it, f.rect) } ?: continue
            val h = held.firstOrNull { iou(it.rect, f.rect) >= 0.5 }
            if (h != null) {
                h.rect = f.rect
                h.f = f
                h.sig = sig
                refreshed.add(h)
            } else {
                held.add(Held(f.rect, f, sig, tMs).also { refreshed.add(it) })
            }
        }
        val it = held.iterator()
        var n = 0
        while (it.hasNext()) {
            val h = it.next()
            if (h in refreshed) continue
            val now = frame?.let { signature(it, h.rect) }
            if (now == null || diff(now, h.sig) > maxDiff || tMs - h.since > maxAgeMs) {
                it.remove()
                continue
            }
            val f = h.f
            out.add(
                Finding(
                    "hold-$lookId-${n++}", f.frameId, lookId, tMs, f.conceptId, f.layer, "hide", 1.0, h.rect,
                    f.scope, "hold"
                )
            )
        }
        return out
    }

    /**
     * Between looks (no AI): re-confirm held covers whose pixels are unchanged in [frame], so a still screen that is
     * only re-examined every few seconds never lets its covers lapse. Changed ones are dropped.
     */
    fun refresh(frame: Frame, lookId: Int, tMs: Long): List<Finding> {
        val out = ArrayList<Finding>()
        val it = held.iterator()
        while (it.hasNext()) {
            val h = it.next()
            val now = signature(frame, h.rect)
            if (now == null || diff(now, h.sig) > maxDiff || tMs - h.since > maxAgeMs) {
                it.remove()
                continue
            }
            val f = h.f
            out.add(
                Finding(
                    "hold-$lookId-r${out.size}", f.frameId, lookId, tMs, f.conceptId, f.layer, "hide", 1.0, h.rect,
                    f.scope, "hold"
                )
            )
        }
        return out
    }

    fun clear() = held.clear()

    companion object {
        private const val G = 8

        /** 8x8 mean luma of [r] (screen px) in the frame's pixels; null if the frame has no pixels. */
        fun signature(f: Frame, r: Rect): IntArray? {
            val argb = f.argb ?: return null
            val m = f.meta
            if (m.width <= 0 || m.height <= 0 || m.screenWidth <= 0 || m.screenHeight <= 0) return null
            val x0 = (r.x.toLong() * m.width / m.screenWidth).toInt().coerceIn(0, m.width - 1)
            val y0 = (r.y.toLong() * m.height / m.screenHeight).toInt().coerceIn(0, m.height - 1)
            val x1 = ((r.x + r.w).toLong() * m.width / m.screenWidth).toInt().coerceIn(x0 + 1, m.width)
            val y1 = ((r.y + r.h).toLong() * m.height / m.screenHeight).toInt().coerceIn(y0 + 1, m.height)
            val out = IntArray(G * G)
            for (gy in 0 until G) {
                for (gx in 0 until G) {
                    val cx = x0 + (x1 - x0) * (2 * gx + 1) / (2 * G)
                    val cy = y0 + (y1 - y0) * (2 * gy + 1) / (2 * G)
                    val c = argb[cy.coerceIn(0, m.height - 1) * m.width + cx.coerceIn(0, m.width - 1)]
                    out[gy * G + gx] = ((c shr 16 and 0xFF) * 77 + (c shr 8 and 0xFF) * 150 + (c and 0xFF) * 29) shr 8
                }
            }
            return out
        }

        fun diff(a: IntArray, b: IntArray): Int {
            var s = 0
            for (i in a.indices) s += kotlin.math.abs(a[i] - b[i])
            return s / a.size
        }

        fun iou(a: Rect, b: Rect): Double {
            val w = minOf(a.x + a.w, b.x + b.w) - maxOf(a.x, b.x)
            val h = minOf(a.y + a.h, b.y + b.h) - maxOf(a.y, b.y)
            if (w <= 0 || h <= 0) return 0.0
            val i = w.toDouble() * h
            return i / (a.w.toDouble() * a.h + b.w.toDouble() * b.h - i)
        }
    }
}
