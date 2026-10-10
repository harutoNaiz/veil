package com.veil.guard.capture.backup

/**
 * Pure coordinator for two independent Android screenshot throttles (per-window and whole-display, each 333 ms).
 * Alternating the kinds, offset from each other, roughly doubles the rate versus a single paced stream.
 */
class DualShotScheduler(private val minGapMs: Long = 150) {
    enum class Kind { WINDOW, DISPLAY }

    private val window = ShotScheduler()
    private val display = ShotScheduler()
    private var lastWindowMs = Long.MIN_VALUE / 2
    private var lastDisplayMs = Long.MIN_VALUE / 2
    private var paused = false

    private fun sched(k: Kind) = if (k == Kind.WINDOW) window else display

    private fun lastOf(k: Kind) = if (k == Kind.WINDOW) lastWindowMs else lastDisplayMs

    private fun dueAt(k: Kind, nowMs: Long): Long {
        val own = nowMs + (sched(k).delayUntilNext(nowMs) ?: 0L)
        val other = lastOf(if (k == Kind.WINDOW) Kind.DISPLAY else Kind.WINDOW)
        return maxOf(own, other + minGapMs)
    }

    /** The earliest-due kind and the delay from [nowMs] until it may be requested; null while paused. */
    fun next(nowMs: Long): Pair<Kind, Long>? {
        if (paused) return null
        val w = dueAt(Kind.WINDOW, nowMs)
        val d = dueAt(Kind.DISPLAY, nowMs)
        // Tie: take the kind requested least recently.
        val kind = if (w < d || (w == d && lastWindowMs <= lastDisplayMs)) Kind.WINDOW else Kind.DISPLAY
        return kind to maxOf(0L, minOf(w, d) - nowMs)
    }

    fun onRequested(kind: Kind, nowMs: Long) {
        sched(kind).onRequested(nowMs)
        if (kind == Kind.WINDOW) lastWindowMs = nowMs else lastDisplayMs = nowMs
    }

    fun onTooShort(kind: Kind) = sched(kind).onIntervalTooShort()

    fun onShot(kind: Kind) = sched(kind).onShot()

    fun pause() {
        paused = true
    }

    fun resume() {
        paused = false
    }
}

/** A window screenshot that fell back to the full display (no full-screen app window): it shows Veil's covers. */
object A11yDisplayFallback {
    const val CODE = -7
}
