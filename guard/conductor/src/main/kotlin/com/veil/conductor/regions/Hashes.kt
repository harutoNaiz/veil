package com.veil.conductor.regions

import com.veil.brain.contract.Rect
import com.veil.brain.gate.THUMB_H
import com.veil.brain.gate.THUMB_W
import com.veil.conductor.Frame

/** Gray 9x8 dHash of a screen-px rect (bit-exact pHash is deferred, see 5.1). */
object Hashes {
    fun dhash64(frame: Frame, rect: Rect): Long {
        val m = frame.meta
        val sw = maxOf(m.screenWidth, 1)
        val sh = maxOf(m.screenHeight, 1)
        val x0 = rect.x.toDouble() / sw
        val y0 = rect.y.toDouble() / sh
        val fw = rect.w.toDouble() / sw
        val fh = rect.h.toDouble() / sh
        val g = Array(8) { r ->
            IntArray(9) { c -> gray(frame, x0 + fw * (c + 0.5) / 9, y0 + fh * (r + 0.5) / 8) }
        }
        var h = 0L
        for (r in 0 until 8) {
            for (c in 0 until 8) if (g[r][c] > g[r][c + 1]) h = h or (1L shl (r * 8 + c))
        }
        return h
    }

    private fun gray(frame: Frame, fx: Double, fy: Double): Int {
        val argb = frame.argb
        if (argb != null && frame.meta.width * frame.meta.height <= argb.size) {
            val x = (fx * frame.meta.width).toInt().coerceIn(0, frame.meta.width - 1)
            val y = (fy * frame.meta.height).toInt().coerceIn(0, frame.meta.height - 1)
            val p = argb[y * frame.meta.width + x]
            return (((p shr 16) and 255) * 299 + ((p shr 8) and 255) * 587 + (p and 255) * 114) / 1000
        }
        val x = (fx * THUMB_W).toInt().coerceIn(0, THUMB_W - 1)
        val y = (fy * THUMB_H).toInt().coerceIn(0, THUMB_H - 1)
        return frame.thumb[y * THUMB_W + x].toInt() and 255
    }
}
