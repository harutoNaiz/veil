package com.veil.guard.capture.source

import com.veil.guard.capture.FrameSize
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class FrameWatchdogTest {
    private fun wd() = FrameWatchdog(3_000, 6_000, 9_000, 12_000, 20_000, 60_000)

    @Test
    fun escalatesOncePerLevel() {
        val w = wd().also { it.arm(0) }
        assertEquals(FrameWatchdog.Action.NONE, w.check(2_900, true))
        assertEquals(FrameWatchdog.Action.POLL, w.check(3_000, true))
        assertEquals(FrameWatchdog.Action.NONE, w.check(4_000, true))
        assertEquals(FrameWatchdog.Action.REATTACH, w.check(6_000, true))
        assertEquals(FrameWatchdog.Action.NONE, w.check(7_000, true))
        assertEquals(FrameWatchdog.Action.NUDGE, w.check(9_000, true))
        assertEquals(FrameWatchdog.Action.RECREATE, w.check(12_000, true))
        assertEquals(FrameWatchdog.Action.NONE, w.check(15_000, true))
        assertEquals(FrameWatchdog.Action.GIVEUP, w.check(20_000, true))
        assertEquals(FrameWatchdog.Action.NONE, w.check(30_000, true))
        assertEquals(FrameWatchdog.Action.RECREATE, w.check(80_000, true))
        assertEquals(FrameWatchdog.Action.NONE, w.check(90_000, true))
    }

    @Test
    fun frameResetsAndReportsPendingAction() {
        val w = wd().also { it.arm(0) }
        w.check(3_000, true)
        w.check(6_000, true)
        assertEquals(FrameWatchdog.Action.REATTACH, w.onFrame(6_500))
        assertEquals(FrameWatchdog.Action.NONE, w.onFrame(6_600))
        assertEquals(FrameWatchdog.Action.NONE, w.check(9_000, true))
        assertEquals(FrameWatchdog.Action.POLL, w.check(9_600, true))
    }

    @Test
    fun inactiveHoldsClock() {
        val w = wd().also { it.arm(0) }
        assertEquals(FrameWatchdog.Action.NONE, w.check(100_000, false))
        assertEquals(FrameWatchdog.Action.NONE, w.check(102_000, true))
        assertEquals(FrameWatchdog.Action.POLL, w.check(103_000, true))
    }

    @Test
    fun gateForceResetIgnoresLateRelease() {
        val g = FrameGate()
        assertTrue(g.tryAcquire(100))
        val e = g.epoch
        assertEquals(5_000L, g.heldMs(5_100))
        assertEquals(1, g.forceReset())
        assertTrue(g.tryAcquire(6_000))
        g.release(e) // stale lease from before the reset
        assertEquals(1, g.outstanding)
        assertFalse(g.tryAcquire(6_001))
        g.release(g.epoch)
        assertEquals(0, g.outstanding)
    }

    @Test
    fun coreReattachAndRecreateOnlyWhenAttached() {
        val states = mutableListOf<String>()
        var attaches = 0
        var detaches = 0
        var recreates = 0
        val port =
            object : DisplayPort {
                override fun create(size: FrameSize, dpi: Int) = Unit

                override fun setSurfaceAttached(on: Boolean) {
                    if (on) attaches++ else detaches++
                }

                override fun resize(size: FrameSize, dpi: Int) = Unit

                override fun nudge() = Unit

                override fun recreateReader() {
                    recreates++
                }
            }
        val c = ScreenSourceCore(port, FrameSize(1080, 2400), 420) { states += it }
        c.start()
        assertTrue(c.reattach())
        assertTrue(c.recreateReader())
        c.pause()
        assertFalse(c.reattach())
        assertFalse(c.recreateReader())
        assertEquals(1, recreates)
        assertEquals(2, detaches)
        assertEquals(2, attaches)
        assertEquals(listOf("created", "attached", "reattached", "reader-recreated", "detached"), states)
    }
}
