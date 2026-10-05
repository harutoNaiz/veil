package com.veil.conductor.text

import kotlin.math.exp

object ToxPrep {
    /** Truncate to [len], pad with [pad] (mask 0), mask 1 on real ids. */
    fun inputs(ids: IntArray, len: Int, pad: Int): Pair<LongArray, LongArray> {
        val x = LongArray(len) { pad.toLong() }
        val m = LongArray(len)
        for (i in 0 until minOf(len, ids.size)) {
            x[i] = ids[i].toLong()
            m[i] = 1L
        }
        return x to m
    }

    fun score(logits: FloatArray): Double = 1.0 / (1.0 + exp(-logits[0].toDouble()))
}
