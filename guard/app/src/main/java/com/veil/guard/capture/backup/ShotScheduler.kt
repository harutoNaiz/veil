package com.veil.guard.capture.backup

/**
 * Pure pacing for accessibility screenshots: >= 333 ms apart, +333 ms backoff on "interval too short", capped at
 * [maxMs] (window screenshots are throttled to roughly one per 0.8 s; an uncapped backoff starved the pipeline).
 */
class ShotScheduler(private val baseMs: Long = 333, private val maxMs: Long = 1000) {
    private var intervalMs = baseMs
    private var lastRequestMs = Long.MIN_VALUE / 2
    private var paused = false

    val currentIntervalMs: Long get() = intervalMs

    /** Delay to wait from [nowMs] before the next request, or null while paused. */
    fun delayUntilNext(nowMs: Long): Long? = if (paused) null else maxOf(0L, lastRequestMs + intervalMs - nowMs)

    fun onRequested(nowMs: Long) {
        lastRequestMs = nowMs
    }

    fun onIntervalTooShort() {
        intervalMs = minOf(intervalMs + baseMs, maxMs)
    }

    fun pause() {
        paused = true
    }

    fun resume() {
        paused = false
    }
}
