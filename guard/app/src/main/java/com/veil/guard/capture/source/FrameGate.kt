package com.veil.guard.capture.source

/** Lease counter: at most one frame outstanding; a new frame while one is outstanding is dropped. */
class FrameGate {
    @get:Synchronized
    var outstanding = 0
        private set

    @get:Synchronized
    var dropped = 0L
        private set

    @Synchronized
    fun tryAcquire(): Boolean {
        if (outstanding >= 1) {
            dropped++
            return false
        }
        outstanding++
        return true
    }

    @Synchronized
    fun release() {
        if (outstanding > 0) outstanding--
    }
}
