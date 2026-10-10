package com.veil.guard.wire

import com.veil.brain.contract.Rect
import com.veil.guard.overlay.OverlayHub

/** Pure-ish: makes a full-display shot look like a window shot (system bars and our covers from the last one). */
object ShotPatch {
    /** Default bar bands when the overlay has not published the content area yet (share of screen height). */
    private const val TOP_DEFAULT = 0.05
    private const val BOTTOM_DEFAULT = 0.05
    private const val MARGIN_PX = 24

    fun patch(argb: IntArray, base: IntArray, w: Int, h: Int, sw: Int, sh: Int, own: List<Rect>) {
        val c = OverlayHub.content
        val top = if (c != null) c.y else (sh * TOP_DEFAULT).toInt()
        val bottom = if (c != null) c.y + c.h else (sh * (1 - BOTTOM_DEFAULT)).toInt()
        copyRows(argb, base, w, 0, ((top + MARGIN_PX).toLong() * h / sh).toInt().coerceIn(0, h))
        copyRows(argb, base, w, ((bottom - MARGIN_PX).toLong() * h / sh).toInt().coerceIn(0, h), h)
        for (r in own) {
            val x0 = ((r.x - MARGIN_PX).toLong() * w / sw).toInt().coerceIn(0, w)
            val x1 = ((r.x + r.w + MARGIN_PX).toLong() * w / sw).toInt().coerceIn(0, w)
            val y0 = ((r.y - MARGIN_PX).toLong() * h / sh).toInt().coerceIn(0, h)
            val y1 = ((r.y + r.h + MARGIN_PX).toLong() * h / sh).toInt().coerceIn(0, h)
            for (y in y0 until y1) System.arraycopy(base, y * w + x0, argb, y * w + x0, x1 - x0)
        }
    }

    private fun copyRows(dst: IntArray, src: IntArray, w: Int, y0: Int, y1: Int) {
        if (y1 > y0) System.arraycopy(src, y0 * w, dst, y0 * w, (y1 - y0) * w)
    }
}
