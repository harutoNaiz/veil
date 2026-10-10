package com.veil.brain.judge

import com.veil.brain.contract.Rect

/**
 * Piece guards applied after the Judge (twin: workshop/twin/guards.py). Pure; every constant is global.
 *
 * flat: a piece with near-uniform pixels (grey std < [FLAT_STD]) can never hide; the caller measures it.
 * container: a tile, crop or whole piece hides only if its tight evidence agrees. A finder box is related to a
 * container when their overlap is >= [RELATED] of the smaller area. AGREE: with related boxes, one must hide.
 * WINS: with related boxes the container never hides (the boxes decide). Without related boxes, unchanged.
 */
object Guards {
    const val FLAT_STD = 6.0
    const val RELATED = 0.5
    const val AGREE = "agree"
    const val WINS = "wins"
    private val CONTAINERS = setOf("tile", "crop", "whole")

    class Piece(val source: String, val rect: Rect)

    private fun inter(a: Rect, b: Rect): Long {
        val w = minOf(a.x + a.w, b.x + b.w) - maxOf(a.x, b.x)
        val h = minOf(a.y + a.h, b.y + b.h) - maxOf(a.y, b.y)
        return maxOf(0, w).toLong() * maxOf(0, h)
    }

    /** [flat] is null when the flat guard is off. [container] is null, [AGREE] or [WINS]. */
    fun apply(
        pieces: List<Piece>,
        hide: List<Boolean>,
        flat: List<Boolean>? = null,
        container: String? = AGREE
    ): List<Boolean> {
        require(pieces.size == hide.size)
        val out = hide.toMutableList()
        if (flat != null) for (i in out.indices) if (flat[i]) out[i] = false
        if (container != null) {
            val finders = pieces.indices.filter { pieces[it].source == "finder" }
            val base = out.toList()
            for (k in pieces.indices) {
                val r = pieces[k].rect
                if (!base[k] || pieces[k].source !in CONTAINERS) continue
                val ra = r.w.toLong() * r.h
                val rel = finders.filter { j ->
                    val b = pieces[j].rect
                    inter(r, b) >= RELATED * minOf(ra, b.w.toLong() * b.h)
                }
                if (rel.isNotEmpty() && (container == WINS || rel.none { base[it] })) out[k] = false
            }
        }
        return out
    }

    /** Grey-level standard deviation (0..255) of a piece given as luma bytes; below [FLAT_STD] means flat. */
    fun isFlat(luma: IntArray): Boolean {
        if (luma.isEmpty()) return true
        val mean = luma.sumOf { it.toDouble() } / luma.size
        val v = luma.sumOf { (it - mean) * (it - mean) } / luma.size
        return Math.sqrt(v) < FLAT_STD
    }
}
