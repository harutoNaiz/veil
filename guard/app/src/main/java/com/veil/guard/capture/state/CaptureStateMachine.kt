package com.veil.guard.capture.state

import com.veil.guard.capture.CaptureState
import com.veil.guard.capture.FrameSize

sealed class CaptureEvent {
    data class ConsentGranted(val entireScreen: Boolean) : CaptureEvent()

    data object ConsentDenied : CaptureEvent()

    data class ProjectionStopped(val cause: String?) : CaptureEvent()

    data object KeyguardLocked : CaptureEvent()

    data object Pause : CaptureEvent()

    data object Resume : CaptureEvent()

    data object UserStop : CaptureEvent()

    data object Restarted : CaptureEvent()

    data class ContentResized(val content: FrameSize, val display: FrameSize) : CaptureEvent()
}

data class Transition(val tMs: Long, val state: CaptureState, val reason: String?)

/** Pure state machine. Illegal events for the current state are ignored (on() returns null). */
class CaptureStateMachine {
    var state: CaptureState = CaptureState.STOPPED
        private set
    var reason: String? = null
        private set

    fun on(e: CaptureEvent, tMs: Long): Transition? {
        val next: Pair<CaptureState, String?> =
            when (e) {
                is CaptureEvent.ConsentGranted ->
                    when (state) {
                        CaptureState.STOPPED, CaptureState.AWAITING_PERMISSION ->
                            CaptureState.RUNNING to (if (e.entireScreen) null else "singleApp")

                        else -> return null
                    }

                CaptureEvent.ConsentDenied ->
                    when (state) {
                        CaptureState.STOPPED, CaptureState.AWAITING_PERMISSION -> CaptureState.STOPPED to null
                        else -> return null
                    }

                is CaptureEvent.ProjectionStopped ->
                    when (state) {
                        CaptureState.RUNNING, CaptureState.PAUSED ->
                            CaptureState.AWAITING_PERMISSION to (e.cause ?: "stopped")

                        else -> return null
                    }

                CaptureEvent.KeyguardLocked ->
                    when (state) {
                        CaptureState.RUNNING, CaptureState.PAUSED -> CaptureState.AWAITING_PERMISSION to "keyguard"
                        else -> return null
                    }

                CaptureEvent.Restarted ->
                    if (state == CaptureState.STOPPED) CaptureState.AWAITING_PERMISSION to "restarted" else return null

                CaptureEvent.Pause ->
                    if (state == CaptureState.RUNNING) CaptureState.PAUSED to null else return null

                CaptureEvent.Resume ->
                    if (state == CaptureState.PAUSED) CaptureState.RUNNING to null else return null

                CaptureEvent.UserStop ->
                    when (state) {
                        CaptureState.RUNNING, CaptureState.PAUSED, CaptureState.AWAITING_PERMISSION ->
                            CaptureState.STOPPED to null

                        else -> return null
                    }

                is CaptureEvent.ContentResized ->
                    if (state == CaptureState.RUNNING &&
                        !EntireScreenCheck.isEntireScreen(e.content, e.display)
                    ) {
                        CaptureState.AWAITING_PERMISSION to "singleApp"
                    } else {
                        return null
                    }
            }
        state = next.first
        reason = next.second
        return Transition(tMs, state, reason)
    }
}
