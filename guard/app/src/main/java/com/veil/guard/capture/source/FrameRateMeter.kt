package com.veil.guard.capture.source

/** Sliding-window fps (1 s and 10 s) over frame timestamps in ms. */
class FrameRateMeter {
    private val stamps = ArrayDeque<Long>()

    @Synchronized
    fun record(tMs: Long) {
        stamps.addLast(tMs)
        while (stamps.isNotEmpty() && stamps.first() < tMs - 10_000) stamps.removeFirst()
    }

    @Synchronized
    fun fps1s(nowMs: Long): Double = count(nowMs, 1_000) / 1.0

    @Synchronized
    fun fps10s(nowMs: Long): Double = count(nowMs, 10_000) / 10.0

    private fun count(nowMs: Long, windowMs: Long): Int = stamps.count { it > nowMs - windowMs && it <= nowMs }
}
