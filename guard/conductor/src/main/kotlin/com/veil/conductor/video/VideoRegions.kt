package com.veil.conductor.video

import com.veil.brain.contract.Rect

/** Finds playing-video areas from frame-to-frame luma motion on the thumbnail. Pure, no Android. */
class VideoRegions(
    private val screenW: Int,
    private val screenH: Int,
    private val cell: Int = 4,
    private val diffThreshold: Double = 6.0
) {
    private var prev: ByteArray? = null
    private var tw = 0
    private var th = 0
    private var masks = IntArray(0)
    private var current: List<Pair<Rect, Long>> = emptyList()

    fun regions(): List<Rect> = current.map { it.first }

    fun onFrame(thumb: ByteArray, tw: Int, th: Int, tMs: Long) {
        val p = prev
        if (p == null || tw != this.tw || th != this.th || p.size != thumb.size) {
            this.tw = tw
            this.th = th
            masks = IntArray(((tw + cell - 1) / cell) * ((th + cell - 1) / cell))
            prev = thumb.copyOf()
            current = emptyList()
            return
        }
        val cols = (tw + cell - 1) / cell
        val rows = (th + cell - 1) / cell
        val changed = BooleanArray(cols * rows)
        var nChanged = 0
        for (cy in 0 until rows) {
            for (cx in 0 until cols) {
                var sum = 0
                var n = 0
                for (y in cy * cell until minOf(th, (cy + 1) * cell)) {
                    for (x in cx * cell until minOf(tw, (cx + 1) * cell)) {
                        val i = y * tw + x
                        sum += Math.abs((thumb[i].toInt() and 0xFF) - (p[i].toInt() and 0xFF))
                        n++
                    }
                }
                if (n > 0 && sum.toDouble() / n > diffThreshold) {
                    changed[cy * cols + cx] = true
                    nChanged++
                }
            }
        }
        prev = thumb.copyOf()
        if (nChanged > 0.7 * changed.size) {
            // scroll / full change: keep old regions, expire stale ones
            current = current.filter { tMs - it.second <= EXPIRE_MS }
            return
        }
        val playing = BooleanArray(changed.size)
        for (i in changed.indices) {
            masks[i] = ((masks[i] shl 1) or (if (changed[i]) 1 else 0)) and 0x3F
            playing[i] = Integer.bitCount(masks[i] and 0x1F) >= 3
        }
        current = components(playing, cols, rows).mapNotNull { toRegion(it, cols) }.map { it to tMs }
    }

    private fun components(playing: BooleanArray, cols: Int, rows: Int): List<List<Int>> {
        val seen = BooleanArray(playing.size)
        val out = ArrayList<List<Int>>()
        for (s in playing.indices) {
            if (!playing[s] || seen[s]) continue
            val comp = ArrayList<Int>()
            val stack = ArrayDeque<Int>()
            stack.addLast(s)
            seen[s] = true
            while (stack.isNotEmpty()) {
                val c = stack.removeLast()
                comp.add(c)
                val x = c % cols
                val y = c / cols
                val nb =
                    intArrayOf(
                        if (x > 0) c - 1 else -1,
                        if (x < cols - 1) c + 1 else -1,
                        if (y > 0) c - cols else -1,
                        if (y < rows - 1) c + cols else -1
                    )
                for (n in nb) {
                    if (n >= 0 && playing[n] && !seen[n]) {
                        seen[n] = true
                        stack.addLast(n)
                    }
                }
            }
            out.add(comp)
        }
        return out
    }

    private fun toRegion(comp: List<Int>, cols: Int): Rect? {
        var x0 = Int.MAX_VALUE
        var y0 = Int.MAX_VALUE
        var x1 = -1
        var y1 = -1
        for (c in comp) {
            val x = c % cols
            val y = c / cols
            x0 = minOf(x0, x)
            y0 = minOf(y0, y)
            x1 = maxOf(x1, x)
            y1 = maxOf(y1, y)
        }
        val boxCells = (x1 - x0 + 1) * (y1 - y0 + 1)
        if (comp.size.toDouble() / boxCells < 0.5) return null
        val px0 = x0 * cell
        val py0 = y0 * cell
        val px1 = minOf(tw, (x1 + 1) * cell)
        val py1 = minOf(th, (y1 + 1) * cell)
        val sx = screenW.toDouble() / tw
        val sy = screenH.toDouble() / th
        val r =
            Rect(
                Math.round(px0 * sx).toInt(),
                Math.round(py0 * sy).toInt(),
                Math.round((px1 - px0) * sx).toInt(),
                Math.round((py1 - py0) * sy).toInt()
            )
        if (r.w < 0.3 * screenW || r.h < 0.08 * screenH) return null
        val maxArea = if (screenW > screenH) 1.0 else 0.7
        if (r.w.toLong() * r.h > maxArea * screenW.toLong() * screenH + 1) return null
        return r
    }

    private companion object {
        const val EXPIRE_MS = 2000L
    }
}
