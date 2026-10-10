package com.veil.guard.capture.source

/**
 * Lease counter: at most one frame outstanding; a new frame while one is outstanding is dropped.
 * [forceReset] frees a lease that was never released (stuck consumer); the epoch makes a late
 * release() from the abandoned lease a no-op so it cannot free somebody else's lease.
 */
class FrameGate {
    @get:Synchronized
    var outstanding = 0
        private set

    @get:Synchronized
    var dropped = 0L
        private set

    @get:Synchronized
    var epoch = 0
        private set

    private var acquiredAtMs = 0L

    @Synchronized
    fun tryAcquire(nowMs: Long = 0L): Boolean {
        if (outstanding >= 1) {
            dropped++
            return false
        }
        outstanding++
        acquiredAtMs = nowMs
        return true
    }

    @Synchronized
    fun release() {
        if (outstanding > 0) outstanding--
    }

    /** Release the lease taken in [epoch]; ignored when the gate was force-reset since. */
    @Synchronized
    fun release(epoch: Int) {
        if (epoch == this.epoch) release()
    }

    /** How long the current lease has been held, or 0 when none. */
    @Synchronized
    fun heldMs(nowMs: Long): Long = if (outstanding > 0) nowMs - acquiredAtMs else 0L

    /** Drop all leases. Returns how many were outstanding. */
    @Synchronized
    fun forceReset(): Int {
        val n = outstanding
        outstanding = 0
        epoch++
        return n
    }
}
