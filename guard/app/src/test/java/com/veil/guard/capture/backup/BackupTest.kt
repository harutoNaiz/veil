package com.veil.guard.capture.backup

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class BackupTest {
    @Test
    fun schedulerKeepsAtLeast333msAndTwoFpsSteady() {
        val s = ShotScheduler()
        var now = 0L
        var shots = 0
        while (now < 10_000) {
            val d = s.delayUntilNext(now)!!
            now += d
            s.onRequested(now)
            shots++
            now += 20 // screenshot latency
        }
        assertTrue("fps ${shots / 10.0}", shots / 10.0 >= 2.0)
        s.onRequested(1000)
        assertTrue(s.delayUntilNext(1100)!! >= 233)
    }

    @Test
    fun neverAsksAtAndroidsRejectBoundary() {
        // Android rejects <= 333 ms after its own stamp of the last request; ours must leave a margin.
        assertTrue(ShotScheduler().currentIntervalMs > 333)
    }

    @Test
    fun backoffAddsInterval() {
        val s = ShotScheduler()
        s.onIntervalTooShort()
        assertEquals(420L, s.currentIntervalMs)
        s.onRequested(0)
        assertEquals(420L, s.delayUntilNext(0))
    }

    @Test
    fun backoffIsCapped() {
        val s = ShotScheduler()
        repeat(30) { s.onIntervalTooShort() }
        assertEquals(1000L, s.currentIntervalMs) // throttled window shots must not starve the pipeline
    }

    @Test
    fun recoversToFullPaceAfterRejections() {
        // The old scheduler only ever slowed down: one burst of rejections held it at ~1 fps for good.
        val s = ShotScheduler()
        repeat(30) { s.onIntervalTooShort() }
        repeat(60) { s.onShot() }
        assertEquals(360L, s.currentIntervalMs)
    }

    @Test
    fun pauseStopsScheduling() {
        val s = ShotScheduler()
        s.pause()
        assertNull(s.delayUntilNext(0))
        s.resume()
        assertEquals(0L, s.delayUntilNext(0))
    }

    @Test
    fun dedupeDropsIdenticalFrames() {
        val d = ThumbDedupe()
        val a = ByteArray(360 * 800) { 50 }
        assertTrue(d.changed(a, 360, 800))
        assertFalse(d.changed(a.copyOf(), 360, 800))
        val b = a.copyOf()
        for (y in 0 until 400) for (x in 0 until 360) b[y * 360 + x] = 120
        assertTrue(d.changed(b, 360, 800))
    }
}
