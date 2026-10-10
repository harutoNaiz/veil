package com.veil.guard.wire

import com.veil.brain.contract.Finding
import com.veil.brain.contract.Record
import com.veil.brain.contract.UiEvent
import com.veil.conductor.AiWorker
import com.veil.conductor.Conductor
import com.veil.conductor.Counters
import com.veil.conductor.DebugLog
import com.veil.conductor.Frame
import com.veil.conductor.Lane
import com.veil.conductor.LayoutNode
import com.veil.conductor.LookInput
import com.veil.conductor.OverlayPort
import com.veil.conductor.StatsSink
import com.veil.conductor.runLanesIsolated

/** Pure wiring: one Conductor + stage log + user pause. All calls except [offer] belong on one thread. */
class GuardCore(
    private val paramsJson: String,
    mode: String,
    private val lanes: (Counters) -> List<Lane>,
    private val worker: AiWorker,
    private val overlay: () -> OverlayPort?,
    private val layout: () -> List<LayoutNode>,
    private val log: DebugLog,
    skipApps: Set<String>,
    private val now: () -> Long,
    private val trace: (String, () -> Unit) -> Unit = { _, b -> b() }
) {
    @Volatile var mode: String = mode
        private set

    @Volatile var userPaused = false
        private set

    @Volatile var lastStats: Record? = null
        private set

    private var skipApps: Set<String> = skipApps
    private val stages = StageTracker { log.write(it) }

    @Volatile private var screenW = 0

    @Volatile private var screenH = 0
    private var planSeq = 0L

    private val port =
        object : OverlayPort {
            override fun submit(plan: Record) {
                overlay()?.submit(plan)
            }

            override fun shift(dx: Int, dy: Int, tMs: Long) {
                overlay()?.shift(dx, dy, tMs)
            }
        }

    private val wrappedLog =
        DebugLog { rec ->
            val k = rec["kind"]
            val out =
                if (k == "plan" || k == "maskPlan") {
                    LinkedHashMap(rec).also { it["lookId"] = stages.lastJudged }
                } else {
                    rec
                }
            log.write(out)
            stages.onRecord(rec)
        }

    private val trackedWorker =
        object : AiWorker {
            override val busy: Boolean get() = worker.busy

            override fun submit(job: () -> List<Finding>, done: (List<Finding>, Long) -> Unit) {
                worker.submit(job) { f, ms ->
                    stages.judged(now())
                    done(f, ms)
                }
            }
        }

    /** Delegates to a swappable lane list so concepts can change without rebuilding the Conductor. */
    class SwapLane(private val log: () -> DebugLog? = { WireHub.log }) : Lane {
        @Volatile var current: List<Lane> = emptyList()

        /** One lane throwing must not drop the others' findings. */
        override fun run(input: LookInput): List<Finding> = runLanesIsolated(current, input, log())
    }

    private val swap = SwapLane { wrappedLog }
    private var counters = Counters()

    var buildCount = 0
        private set

    @Volatile private var conductor: Conductor = build()

    private fun build(): Conductor {
        buildCount++
        counters = Counters()
        swap.current = lanes(counters)
        val sentinel =
            Lane {
                stages.ai(it.lookId, now())
                emptyList()
            }
        return Conductor(
            if (mode == "off") "balanced" else mode,
            paramsJson,
            listOf(swap, sentinel),
            trackedWorker,
            port,
            StatsSink { lastStats = it },
            wrappedLog,
            counters,
            skipApps,
            layout,
            idleLookMs = IDLE_LOOK_MS,
            selfCaptureHold = false,
            holdMsOverride = 1200, // a moved/closed picture must not leave its cover behind (was 3000)
            videoCovers = com.veil.guard.wire.ml.LiveLanes.fullCover,
            instantProb = 0.97
        )
    }

    fun offer(f: Frame) {
        if (userPaused) return
        screenW = f.meta.screenWidth
        screenH = f.meta.screenHeight
        stages.frame(f.meta.frameId, now())
        conductor.offer(f)
    }

    fun pump() {
        if (userPaused) return
        trace("veil.step") { conductor.pump() }
    }

    fun onEvent(e: UiEvent) = conductor.onEvent(e)

    fun onDrawn(tMs: Long) = stages.onDrawn(tMs)

    fun pause() {
        if (userPaused) return
        userPaused = true
        overlay()?.submit(PlanRecords.empty(++planSeq, now(), screenW, screenH))
    }

    fun resume() {
        userPaused = false
    }

    fun setMode(m: String) {
        mode = m
        if (m == "off") {
            pause()
        } else {
            rebuild()
            resume()
        }
    }

    fun setSkipApps(s: Set<String>) {
        skipApps = s
        rebuild()
    }

    fun swapLanes() {
        swap.current = lanes(counters)
        conductor.videoCovers = com.veil.guard.wire.ml.LiveLanes.fullCover
    }

    fun rebuild() {
        conductor = build()
    }

    private companion object {
        /** A still screen is re-checked this often, so unchanged content (static bison page) still gets covered. */
        const val IDLE_LOOK_MS = 2500L // re-check a still screen (was 1 s: kept the AI busy and the phone hot)
    }
}
