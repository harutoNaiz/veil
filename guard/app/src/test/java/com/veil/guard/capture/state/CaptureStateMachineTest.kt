package com.veil.guard.capture.state

import com.veil.guard.capture.CaptureState
import com.veil.guard.capture.FrameSize
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class CaptureStateMachineTest {
    @Test
    fun consentGrantedEntireScreenRuns() {
        val m = CaptureStateMachine()
        val t = m.on(CaptureEvent.ConsentGranted(entireScreen = true), 100)
        assertEquals(CaptureState.RUNNING, t?.state)
        assertNull(t?.reason)
    }

    @Test
    fun consentGrantedSingleAppRunsWithReason() {
        val m = CaptureStateMachine()
        val t = m.on(CaptureEvent.ConsentGranted(entireScreen = false), 100)
        assertEquals(CaptureState.RUNNING, t?.state)
        assertEquals("singleApp", t?.reason)
    }

    @Test
    fun pauseThenResumeNeverRequestsConsent() {
        val m = CaptureStateMachine()
        m.on(CaptureEvent.ConsentGranted(entireScreen = true), 0)
        val paused = m.on(CaptureEvent.Pause, 10)
        assertEquals(CaptureState.PAUSED, paused?.state)
        assertNull(paused?.reason)
        val resumed = m.on(CaptureEvent.Resume, 20)
        assertEquals(CaptureState.RUNNING, resumed?.state)
        assertNull(resumed?.reason)
    }

    @Test
    fun userStopFromRunningStops() {
        val m = CaptureStateMachine()
        m.on(CaptureEvent.ConsentGranted(entireScreen = true), 0)
        val t = m.on(CaptureEvent.UserStop, 10)
        assertEquals(CaptureState.STOPPED, t?.state)
    }

    @Test
    fun projectionStoppedReportsAwaitingAtSameTMs() {
        val m = CaptureStateMachine()
        m.on(CaptureEvent.ConsentGranted(entireScreen = true), 0)
        val t = m.on(CaptureEvent.ProjectionStopped(cause = "revoked"), 500)
        assertEquals(CaptureState.AWAITING_PERMISSION, t?.state)
        assertEquals(500L, t?.tMs)
        assertEquals("revoked", t?.reason)
    }

    @Test
    fun keyguardLockedSetsKeyguardReason() {
        val m = CaptureStateMachine()
        m.on(CaptureEvent.ConsentGranted(entireScreen = true), 0)
        val t = m.on(CaptureEvent.KeyguardLocked, 10)
        assertEquals(CaptureState.AWAITING_PERMISSION, t?.state)
        assertEquals("keyguard", t?.reason)
    }

    @Test
    fun illegalEventsAreIgnored() {
        val m = CaptureStateMachine()
        val t = m.on(CaptureEvent.Resume, 10)
        assertNull(t)
        assertEquals(CaptureState.STOPPED, m.state)
    }

    @Test
    fun contentResizedSingleAppTriggersAwaiting() {
        val m = CaptureStateMachine()
        m.on(CaptureEvent.ConsentGranted(entireScreen = true), 0)
        val t =
            m.on(
                CaptureEvent.ContentResized(FrameSize(500, 1000), FrameSize(1080, 2400)),
                10
            )
        assertEquals(CaptureState.AWAITING_PERMISSION, t?.state)
        assertEquals("singleApp", t?.reason)
    }

    @Test
    fun contentResizedMatchingDisplayStaysRunning() {
        val m = CaptureStateMachine()
        m.on(CaptureEvent.ConsentGranted(entireScreen = true), 0)
        val t =
            m.on(
                CaptureEvent.ContentResized(FrameSize(1080, 2400), FrameSize(1080, 2400)),
                10
            )
        assertNull(t)
        assertEquals(CaptureState.RUNNING, m.state)
    }

    @Test
    fun restartedFromStoppedAwaitsPermission() {
        val m = CaptureStateMachine()
        val t = m.on(CaptureEvent.Restarted, 1)
        assertEquals(CaptureState.AWAITING_PERMISSION, t?.state)
        assertEquals("restarted", t?.reason)
        assertNull(m.on(CaptureEvent.Restarted, 2))
    }
}
