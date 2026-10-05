package com.veil.runtime

import kotlin.math.ceil

data class Latency(val n: Int, val p50: Double, val p95: Double, val max: Double, val mean: Double)

fun latencyOf(ms: DoubleArray): Latency {
    require(ms.isNotEmpty()) { "no samples" }
    val s = ms.sortedArray()
    fun pct(p: Double): Double = s[ceil(p * s.size).toInt().coerceIn(1, s.size) - 1]
    return Latency(s.size, pct(0.5), pct(0.95), s.last(), s.average())
}
