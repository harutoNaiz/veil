package com.veil.guard.capture.blind

import com.veil.guard.capture.PxRect

/** Finds black (capture-protected) areas in a luma plane. Pure. */
object BlindSpotDetector {
    const val BLACK_LUMA = 16
    const val MAX_RECTS = 16
    private const val CELL = 8
    private val NEIGHBOURS = listOf(1 to 0, -1 to 0, 0 to 1, 0 to -1)

    fun detect(luma: ByteArray, w: Int, h: Int, hints: List<PxRect>): List<PxRect> {
        if (w <= 0 || h <= 0 || luma.size < w * h) return emptyList()
        if (blackFraction(luma, w, 0, 0, w, h) >= 0.95) return listOf(PxRect(0, 0, w, h))
        val out = ArrayList<PxRect>()
        for (r in hints) {
            val x0 = r.x.coerceIn(0, w)
            val y0 = r.y.coerceIn(0, h)
            val x1 = (r.x + r.w).coerceIn(0, w)
            val y1 = (r.y + r.h).coerceIn(0, h)
            if (x1 > x0 && y1 > y0 && blackFraction(luma, w, x0, y0, x1, y1) >= 0.9) {
                out.add(PxRect(x0, y0, x1 - x0, y1 - y0))
            }
        }
        if (out.isEmpty()) cellRegions(luma, w, h, out)
        return out.take(MAX_RECTS)
    }

    private fun cellRegions(luma: ByteArray, w: Int, h: Int, out: MutableList<PxRect>) {
        val cols = (w + CELL - 1) / CELL
        val rows = (h + CELL - 1) / CELL
        val black = BooleanArray(cols * rows)
        for (cy in 0 until rows) {
            for (cx in 0 until cols) {
                val x1 = minOf(w, (cx + 1) * CELL)
                val y1 = minOf(h, (cy + 1) * CELL)
                black[cy * cols + cx] = blackFraction(luma, w, cx * CELL, cy * CELL, x1, y1) >= 0.99
            }
        }
        val seen = BooleanArray(cols * rows)
        val stack = ArrayDeque<Int>()
        for (start in black.indices) {
            if (!black[start] || seen[start]) continue
            var minX = cols
            var minY = rows
            var maxX = -1
            var maxY = -1
            var count = 0
            seen[start] = true
            stack.addLast(start)
            while (stack.isNotEmpty()) {
                val i = stack.removeLast()
                val cx = i % cols
                val cy = i / cols
                count++
                minX = minOf(minX, cx)
                maxX = maxOf(maxX, cx)
                minY = minOf(minY, cy)
                maxY = maxOf(maxY, cy)
                for ((dx, dy) in NEIGHBOURS) {
                    val nx = cx + dx
                    val ny = cy + dy
                    if (nx !in 0 until cols || ny !in 0 until rows) continue
                    val j = ny * cols + nx
                    if (black[j] && !seen[j]) {
                        seen[j] = true
                        stack.addLast(j)
                    }
                }
            }
            val px = minX * CELL
            val py = minY * CELL
            val rect = PxRect(px, py, minOf(w, (maxX + 1) * CELL) - px, minOf(h, (maxY + 1) * CELL) - py)
            if (count.toLong() * CELL * CELL * 4 >= w.toLong() * h) out.add(rect)
        }
    }

    private fun blackFraction(luma: ByteArray, w: Int, x0: Int, y0: Int, x1: Int, y1: Int): Double {
        var n = 0
        for (y in y0 until y1) {
            val row = y * w
            for (x in x0 until x1) if ((luma[row + x].toInt() and 0xFF) < BLACK_LUMA) n++
        }
        val total = (x1 - x0) * (y1 - y0)
        return if (total <= 0) 0.0 else n.toDouble() / total
    }
}
