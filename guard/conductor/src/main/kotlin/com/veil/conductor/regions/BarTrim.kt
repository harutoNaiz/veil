package com.veil.conductor.regions

import com.veil.brain.contract.Rect

/** Trims flat black/white letterbox bars off a rect (a photo view node often spans the bars around the photo). */
object BarTrim {
    private fun lum(p: Int): Int = maxOf((p shr 16) and 255, (p shr 8) and 255, p and 255)

    private fun minc(p: Int): Int = minOf((p shr 16) and 255, (p shr 8) and 255, p and 255)

    /** A sampled line is a bar when >= 98% of its samples are near-black or all are near-white. */
    private fun bar(argb: IntArray, fw: Int, x0: Int, y0: Int, x1: Int, y1: Int, horizontal: Boolean): Boolean {
        val n = if (horizontal) x1 - x0 else y1 - y0
        val step = maxOf(1, n / 48)
        var dark = 0
        var light = 0
        var total = 0
        var i = 0
        while (i < n) {
            val p = if (horizontal) argb[y0 * fw + x0 + i] else argb[(y0 + i) * fw + x0]
            if (lum(p) <= 24) dark++
            if (minc(p) >= 235) light++
            total++
            i += step
        }
        return dark * 100 >= total * 98 || light == total
    }

    /** rect in screen px; returns the trimmed rect in screen px (unchanged if no bars or too little would remain). */
    fun trim(argb: IntArray, fw: Int, fh: Int, sw: Int, sh: Int, r: Rect): Rect {
        val sx = fw.toDouble() / sw
        val sy = fh.toDouble() / sh
        var x0 = (r.x * sx).toInt().coerceIn(0, fw - 1)
        var y0 = (r.y * sy).toInt().coerceIn(0, fh - 1)
        var x1 = ((r.x + r.w) * sx).toInt().coerceIn(x0 + 1, fw)
        var y1 = ((r.y + r.h) * sy).toInt().coerceIn(y0 + 1, fh)
        val minW = maxOf(1, (x1 - x0) / 4)
        val minH = maxOf(1, (y1 - y0) / 4)
        while (y1 - y0 > minH && bar(argb, fw, x0, y0, x1, y0 + 1, true)) y0++
        while (y1 - y0 > minH && bar(argb, fw, x0, y1 - 1, x1, y1, true)) y1--
        while (x1 - x0 > minW && bar(argb, fw, x0, y0, x0 + 1, y1, false)) x0++
        while (x1 - x0 > minW && bar(argb, fw, x1 - 1, y0, x1, y1, false)) x1--
        val nx = Math.rint(x0 / sx).toInt().coerceIn(0, sw)
        val ny = Math.rint(y0 / sy).toInt().coerceIn(0, sh)
        val ex = Math.rint(x1 / sx).toInt().coerceIn(nx + 1, sw)
        val ey = Math.rint(y1 / sy).toInt().coerceIn(ny + 1, sh)
        val out = Rect(nx, ny, ex - nx, ey - ny)
        // Only accept a real change (>= 4% of the node): avoids jitter from dark photo edges.
        return if (out.w.toLong() * out.h > r.w.toLong() * r.h * 96 / 100) r else out
    }
}
