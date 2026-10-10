package com.veil.guard.capture.source

/**
 * Pure "no frames while the display is on" detector. A virtual display only produces frames when the
 * screen content changes, so silence alone is ambiguous: actions escalate and then back off.
 * poll (acquire without the listener) -> reattach (setSurface null/surface) -> nudge (dpi flip) -> recreate reader
 * -> giveup (a fresh surface got no frame either, so the pipe is dead, not idle); then recreate every [repeatMs].
 */
class FrameWatchdog(
    private val pollMs: Long = 3_000,
    private val reattachMs: Long = 6_000,
    private val nudgeMs: Long = 9_000,
    private val recreateMs: Long = 12_000,
    private val giveupMs: Long = 20_000,
    private val repeatMs: Long = 60_000
) {
    enum class Action { NONE, POLL, REATTACH, NUDGE, RECREATE, GIVEUP }

    private var lastFrameMs = 0L
    private var lastActionMs = Long.MIN_VALUE
    private var stage = 0

    /** Last action taken since the previous frame, for "recovered after X" logging. */
    var lastAction: Action = Action.NONE
        private set

    fun arm(nowMs: Long) {
        lastFrameMs = nowMs
        lastActionMs = Long.MIN_VALUE
        stage = 0
        lastAction = Action.NONE
    }

    /** Returns the action that was pending when a frame arrived (NONE if the pipe was healthy). */
    fun onFrame(nowMs: Long): Action {
        val pending = lastAction
        lastFrameMs = nowMs
        lastActionMs = Long.MIN_VALUE
        stage = 0
        lastAction = Action.NONE
        return pending
    }

    fun silentMs(nowMs: Long): Long = nowMs - lastFrameMs

    /** [active] = display on and not paused. While inactive the silence clock is held at zero. */
    fun check(nowMs: Long, active: Boolean): Action {
        if (!active) {
            lastFrameMs = nowMs
            lastActionMs = Long.MIN_VALUE
            stage = 0
            return Action.NONE
        }
        val silent = nowMs - lastFrameMs
        val want =
            when {
                silent >= giveupMs -> Action.GIVEUP
                silent >= recreateMs -> Action.RECREATE
                silent >= nudgeMs -> Action.NUDGE
                silent >= reattachMs -> Action.REATTACH
                silent >= pollMs -> Action.POLL
                else -> Action.NONE
            }
        if (want == Action.NONE) return Action.NONE
        val level = want.ordinal
        // each level fires once per silence episode; after GIVEUP, RECREATE repeats slowly
        val repeat = stage == Action.GIVEUP.ordinal && nowMs - lastActionMs >= repeatMs
        if (level <= stage && !repeat) return Action.NONE
        val act = if (level > stage) want else Action.RECREATE
        stage = maxOf(stage, level)
        lastActionMs = nowMs
        lastAction = act
        return act
    }
}
