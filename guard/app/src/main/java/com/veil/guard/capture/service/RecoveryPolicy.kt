package com.veil.guard.capture.service

import com.veil.guard.capture.CaptureState
import com.veil.guard.capture.state.CaptureEvent

enum class FgsKind { PROJECTION, WAITING }

data class StartDecision(val fgs: FgsKind, val event: CaptureEvent?, val stopSelf: Boolean)

/** Pure decision for CaptureService.onStartCommand (no android.*). */
object RecoveryPolicy {
    fun onStart(action: String?, consentOk: Boolean, hasProjection: Boolean, wasRunning: Boolean): StartDecision =
        when {
            consentOk || hasProjection -> StartDecision(FgsKind.PROJECTION, null, false)
            action == null && wasRunning -> StartDecision(FgsKind.WAITING, CaptureEvent.Restarted, false)
            action == null -> StartDecision(FgsKind.WAITING, null, true)
            else -> StartDecision(FgsKind.WAITING, null, false)
        }

    fun wasRunning(s: CaptureState): Boolean = when (s) {
        CaptureState.RUNNING, CaptureState.PAUSED, CaptureState.AWAITING_PERMISSION -> true
        CaptureState.STOPPED -> false
    }
}
