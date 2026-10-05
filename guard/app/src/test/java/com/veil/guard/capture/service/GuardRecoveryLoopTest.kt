package com.veil.guard.capture.service

import com.veil.guard.capture.CaptureState
import com.veil.guard.capture.state.CaptureEvent
import com.veil.guard.capture.state.CaptureStateMachine
import org.junit.Assert.assertTrue
import org.junit.Test

class GuardRecoveryLoopTest {
    private fun running(): CaptureStateMachine =
        CaptureStateMachine().also { it.on(CaptureEvent.ConsentGranted(true), 0) }

    private fun crashOnce(): Boolean {
        val persisted = RecoveryPolicy.wasRunning(running().state)
        val m = CaptureStateMachine()
        val d = RecoveryPolicy.onStart(null, false, false, persisted)
        d.event?.let { m.on(it, 1) }
        if (d.event != CaptureEvent.Restarted || m.state != CaptureState.AWAITING_PERMISSION) return false
        m.on(CaptureEvent.ConsentGranted(true), 2)
        return m.state == CaptureState.RUNNING
    }

    private fun lockOnce(): Boolean {
        val m = running()
        m.on(CaptureEvent.KeyguardLocked, 1)
        if (m.state != CaptureState.AWAITING_PERMISSION) return false
        m.on(CaptureEvent.ConsentGranted(true), 2)
        return m.state == CaptureState.RUNNING
    }

    private fun killOnce(): Boolean {
        val m = running()
        m.on(CaptureEvent.UserStop, 1)
        val d = RecoveryPolicy.onStart(null, false, false, RecoveryPolicy.wasRunning(m.state))
        if (m.state != CaptureState.STOPPED || !d.stopSelf) return false
        m.on(CaptureEvent.ConsentGranted(true), 2)
        return m.state == CaptureState.RUNNING
    }

    @Test
    fun recoveryLoops() {
        val crash = (1..5).count { crashOnce() }
        val lock = (1..5).count { lockOnce() }
        val kill = (1..5).count { killOnce() }
        println("RECOVERY-GUARD crash=$crash/5 lock=$lock/5 kill=$kill/5")
        assertTrue(crash == 5 && lock == 5 && kill == 5)
    }
}
