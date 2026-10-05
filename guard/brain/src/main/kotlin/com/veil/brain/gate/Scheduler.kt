package com.veil.brain.gate

import com.veil.brain.contract.Rect

val IMMEDIATE = listOf("sceneCut", "appChange", "swipe", "revealedStrip")
private const val NEVER = -1_000_000_000L

data class ModeParams(
    val rate: Int,
    val checkupMs: Int,
    val minImmediateGapMs: Int,
    val hotMs: Int = 3000,
    val hotRateMul: Int = 2,
    val throttleDiv: Int = 2,
    val burstGapMs: Int = 150,
    val deadlineMs: Int = 200,
    val skipPackages: List<String> = emptyList()
)

data class Tick(
    val tMs: Long,
    val frameId: Int,
    val screenW: Int,
    val screenH: Int,
    val changedTiles: Int = 0,
    val sceneCut: Boolean = false,
    val revealedRect: Rect? = null,
    val changedRect: Rect? = null,
    val scrollDy: Int = 0,
    val windowChanged: Boolean = false,
    val packageName: String? = null,
    val screenOn: Boolean? = null,
    val busy: Boolean = false,
    val hotHint: Boolean = false,
    val throttle: Boolean = false
)

data class SchedState(
    val phase: String = "watching",
    val screenOn: Boolean = true,
    val packageName: String = "",
    val lastLookMs: Long = NEVER,
    val lastImmediateMs: Long = NEVER,
    val lastCheckupMs: Long = NEVER,
    val lastScrollMs: Long = NEVER,
    val hotUntilMs: Long = NEVER,
    val pending: String? = null,
    val skipped: Int = 0,
    val looks: Int = 0,
    val lastReason: String = "none"
)

data class LookRequest(val why: String, val rect: Rect, val deadlineMs: Long, val frameId: Int, val tMs: Long)

object Scheduler {
    fun cdiv(a: Long, b: Long): Long = -Math.floorDiv(-a, b)

    fun better(a: String?, b: String): String = if (a == null || IMMEDIATE.indexOf(b) < IMMEDIATE.indexOf(a)) b else a

    fun step(state: SchedState, tick: Tick, p: ModeParams): Pair<SchedState, LookRequest?> {
        val t = tick.tMs
        val screenOn = tick.screenOn ?: state.screenOn
        val pkg = tick.packageName ?: state.packageName
        val windowChanged = tick.windowChanged || tick.screenOn == true
        val scrolled = tick.scrollDy != 0
        val lastScroll = if (scrolled) t else state.lastScrollMs
        var hotUntil = state.hotUntilMs

        if (!screenOn || pkg in p.skipPackages) {
            val idle = state.copy(
                phase = "idle",
                screenOn = screenOn,
                packageName = pkg,
                pending = null,
                lastScrollMs = lastScroll,
                lastReason = "none"
            )
            return Pair(idle, null)
        }
        val phase: String
        if (tick.throttle) {
            phase = "throttled"
        } else if (tick.hotHint || t < hotUntil) {
            phase = "hot"
            if (tick.hotHint) hotUntil = t + p.hotMs
        } else {
            phase = "watching"
        }

        var pending = state.pending
        if (tick.sceneCut) pending = better(pending, "sceneCut")
        if (windowChanged) pending = better(pending, "appChange")
        if (scrolled && t - state.lastScrollMs > p.burstGapMs) pending = better(pending, "swipe")
        if (tick.revealedRect != null) pending = better(pending, "revealedStrip")

        val gap = when (phase) {
            "hot" -> cdiv(1000, (p.rate * p.hotRateMul).toLong())
            "throttled" -> cdiv(1000L * p.throttleDiv, p.rate.toLong())
            else -> cdiv(1000, p.rate.toLong())
        }
        val checkupPeriod = p.checkupMs.toLong() * (if (phase == "throttled") p.throttleDiv else 1)

        var want: String? = null
        if (pending != null && t - state.lastImmediateMs >= p.minImmediateGapMs) {
            want = pending
        } else if (t - state.lastCheckupMs >= checkupPeriod) {
            want = "checkup"
        } else if (tick.changedTiles > 0 && t - state.lastLookMs >= gap) {
            want = "periodic"
        }
        if (want != null && phase == "throttled" && t - state.lastLookMs < gap) want = null

        val base = state.copy(
            phase = phase,
            screenOn = screenOn,
            packageName = pkg,
            pending = pending,
            lastScrollMs = lastScroll,
            hotUntilMs = hotUntil,
            lastReason = "none"
        )
        if (want == null) return Pair(base, null)
        if (tick.busy) return Pair(base.copy(skipped = state.skipped + 1, lastReason = "busy"), null)

        val full = Rect(0, 0, tick.screenW, tick.screenH)
        val rect = when (want) {
            "revealedStrip" -> tick.revealedRect ?: full
            "periodic" -> tick.changedRect ?: full
            else -> full
        }
        val ns = base.copy(
            pending = null,
            looks = state.looks + 1,
            lastLookMs = t,
            lastImmediateMs = if (want in IMMEDIATE) t else state.lastImmediateMs,
            lastCheckupMs = if (rect == full) t else state.lastCheckupMs,
            lastReason = want
        )
        return Pair(ns, LookRequest(want, rect, t + p.deadlineMs, tick.frameId, t))
    }
}
