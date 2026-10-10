package com.veil.conductor.regions

import com.veil.brain.contract.Rect
import com.veil.conductor.Frame
import kotlin.math.roundToInt
import kotlin.math.sqrt

/**
 * Finds the picture an object sits in from the pixels alone: starting at the object's box, each side moves outward
 * while the next column/row still has texture, and stops at a flat strip (the gutter or page background around a
 * photo). Works in any app, including web pages that expose no image elements. Pure; frame pixels only.
 */
object PictureEdges {
    /** Strip luma standard deviation below this = flat (gutter, page background). */
    const val FLAT_STD = 7.0

    /** Each side may grow by at most this fraction of the box size (an object fills much of its picture). */
    const val MAX_GROW = 1.5

    /** A snapped picture larger than this share of the screen is not a picture in a feed: keep the box. */
    const val MAX_SCREEN_PCT = 40

    fun snap(f: Frame, r: Rect): Rect {
        val px = f.argb ?: return r
        val m = f.meta
        val fw = m.width
        val fh = m.height
        if (fw <= 0 || fh <= 0 || m.screenWidth <= 0 || m.screenHeight <= 0) return r
        val sx = fw.toDouble() / m.screenWidth
        val sy = fh.toDouble() / m.screenHeight
        var x0 = (r.x * sx).toInt().coerceIn(0, fw - 1)
        var y0 = (r.y * sy).toInt().coerceIn(0, fh - 1)
        var x1 = ((r.x + r.w) * sx).roundToInt().coerceIn(x0 + 1, fw)
        var y1 = ((r.y + r.h) * sy).roundToInt().coerceIn(y0 + 1, fh)
        val gx = ((x1 - x0) * MAX_GROW).toInt() + 1
        val gy = ((y1 - y0) * MAX_GROW).toInt() + 1
        val lx0 = (x0 - gx).coerceAtLeast(0)
        val lx1 = (x1 + gx).coerceAtMost(fw)
        val ly0 = (y0 - gy).coerceAtLeast(0)
        val ly1 = (y1 + gy).coerceAtMost(fh)

        fun luma(x: Int, y: Int): Int {
            val c = px[y * fw + x]
            return ((c shr 16 and 0xFF) * 77 + (c shr 8 and 0xFF) * 150 + (c and 0xFF) * 29) shr 8
        }

        fun flat(n: Int, at: (Int) -> Int): Boolean {
            if (n <= 1) return true
            var s = 0.0
            var s2 = 0.0
            for (i in 0 until n) {
                val v = at(i).toDouble()
                s += v
                s2 += v * v
            }
            val mean = s / n
            return sqrt(maxOf(0.0, s2 / n - mean * mean)) < FLAT_STD
        }

        fun flatCol(x: Int) = flat(y1 - y0) { luma(x, y0 + it) }
        fun flatRow(y: Int) = flat(x1 - x0) { luma(x0 + it, y) }

        repeat(2) {
            // the second pass uses the grown span of the other axis
            while (x0 > lx0 && !flatCol(x0 - 1)) x0--
            while (x1 < lx1 && !flatCol(x1)) x1++
            while (y0 > ly0 && !flatRow(y0 - 1)) y0--
            while (y1 < ly1 && !flatRow(y1)) y1++
        }
        val ox = (x0 / sx).roundToInt()
        val oy = (y0 / sy).roundToInt()
        val out =
            Rect(ox, oy, ((x1 / sx).roundToInt() - ox).coerceAtLeast(1), ((y1 / sy).roundToInt() - oy).coerceAtLeast(1))
        // No clear picture edge (textured full-screen UI): keep the object's own box rather than a huge cover.
        val big = out.w.toLong() * out.h * 100 > m.screenWidth.toLong() * m.screenHeight * MAX_SCREEN_PCT
        return if (big) r else out
    }
}
