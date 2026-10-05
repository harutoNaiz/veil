package com.veil.guard.capture.service

import com.veil.guard.capture.CaptureState
import com.veil.guard.capture.state.CaptureEvent
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class RecoveryPolicyTest {
    @Test
    fun consentOkOrProjectionIsProjection() {
        assertEquals(FgsKind.PROJECTION, RecoveryPolicy.onStart("x", true, false, false).fgs)
        assertEquals(FgsKind.PROJECTION, RecoveryPolicy.onStart(null, false, true, true).fgs)
    }

    @Test
    fun stickyRestartWasRunningRestarts() {
        val d = RecoveryPolicy.onStart(null, false, false, true)
        assertEquals(FgsKind.WAITING, d.fgs)
        assertEquals(CaptureEvent.Restarted, d.event)
        assertFalse(d.stopSelf)
    }

    @Test
    fun stickyRestartNotRunningStops() {
        val d = RecoveryPolicy.onStart(null, false, false, false)
        assertEquals(FgsKind.WAITING, d.fgs)
        assertNull(d.event)
        assertTrue(d.stopSelf)
    }

    @Test
    fun otherActionWaits() {
        val d = RecoveryPolicy.onStart("cmd", false, false, true)
        assertEquals(StartDecision(FgsKind.WAITING, null, false), d)
    }

    @Test
    fun wasRunningMapping() {
        assertTrue(RecoveryPolicy.wasRunning(CaptureState.RUNNING))
        assertTrue(RecoveryPolicy.wasRunning(CaptureState.PAUSED))
        assertTrue(RecoveryPolicy.wasRunning(CaptureState.AWAITING_PERMISSION))
        assertFalse(RecoveryPolicy.wasRunning(CaptureState.STOPPED))
    }
}
