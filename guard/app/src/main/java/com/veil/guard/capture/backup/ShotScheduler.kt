package com.veil.guard.capture.backup

/**
 * Pure pacing for accessibility screenshots. Android rejects a request made <= 333 ms after the last one of the
 * same kind (stamped when the request reaches the system, and a rejected request restarts that timer). Asking at
 * exactly 333 ms by our own clock was therefore rejected, the old +333 ms backoff then held the guard at about one
 * frame per second for good. Now: [baseMs] leaves a small margin above 333 ms, a rejection backs off a little, and
 * every delivered shot steps back towards [baseMs], so the pace settles just above Android's limit (~2.8 fps).
 */
class ShotScheduler(private val baseMs: Long = 360, private val maxMs: Long = 1000, private val stepMs: Long = 60) {
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
        intervalMs = minOf(intervalMs + stepMs, maxMs)
    }

    /** A shot arrived: drift back towards the fastest allowed pace. */
    fun onShot() {
        intervalMs = maxOf(baseMs, intervalMs - stepMs / 3)
    }

    fun pause() {
        paused = true
    }

    fun resume() {
        paused = false
    }
}
