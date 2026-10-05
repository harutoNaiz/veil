package com.veil.guard.signals

import kotlin.math.abs

/** Estimates vertical content shift between two grey row profiles (SAD search). */
object FrameShiftEstimator {
    private const val MAX_MEAN_ERR = 3.0
    private const val MIN_OVERLAP = 8

    /** prev/cur are mean-grey-per-row profiles of length h. Returns content-moved dy, or null if unsure. */
    @Suppress("UNUSED_PARAMETER")
    fun estimate(prev: IntArray, cur: IntArray, w: Int, h: Int, maxShift: Int): Int? {
        if (prev.size < h || cur.size < h || h <= 0) return null
        var best = Double.MAX_VALUE
        var bestS = 0
        var e0 = 0.0
        for (s in -maxShift..maxShift) {
            val n = h - abs(s)
            if (n < MIN_OVERLAP) continue
            var sum = 0L
            for (y in maxOf(0, s) until minOf(h, h + s)) sum += abs(cur[y] - prev[y - s])
            val e = sum.toDouble() / n
            if (s == 0) e0 = e
            if (e < best || (e == best && abs(s) < abs(bestS))) {
                best = e
                bestS = s
            }
        }
        if (bestS == 0 || best > MAX_MEAN_ERR || best > 0.4 * e0) return null
        return bestS
    }
}
