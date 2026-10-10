package com.veil.conductor

import com.veil.brain.contract.Finding
import com.veil.brain.contract.FrameMeta
import com.veil.brain.contract.Record
import com.veil.brain.contract.Rect
import com.veil.brain.contract.UiEvent
import com.veil.brain.cover.plan
import com.veil.brain.motion.BrainPipeline
import java.util.ArrayDeque
import java.util.concurrent.atomic.AtomicReference

/** Drives one BrainPipeline: 1-slot frame mailbox, one look in flight, never a queue. */
class Conductor(
    private val mode: String,
    paramsJson: String,
    private val lanes: List<Lane>,
    private val worker: AiWorker,
    private val overlay: OverlayPort,
    private val stats: StatsSink,
    private val log: DebugLog,
    private val counters: Counters,
    private val skipApps: Set<String>,
    private val layout: () -> List<LayoutNode>,
    /** Re-plans on the last frame when a look delivers findings and no new frame is waiting (static screens). */
    private val autoSettle: Boolean = true,
    /** > 0: a still screen still gets a full look every this many ms (live app); 0 = only the gate decides (tapes). */
    private val idleLookMs: Long = 0,
    /** See BrainPipeline.selfCaptureHold. */
    selfCaptureHold: Boolean = true,
    holdMsOverride: Int = 0
) {
    private val pipeline =
        BrainPipeline(mode, paramsJson, selfCaptureHold = selfCaptureHold, holdMsOverride = holdMsOverride)
    private val lock = Any()
    private val slot = AtomicReference<Frame?>(null)

    @Volatile var paused = false
        private set

    @Volatile var lastPlan: Record? = null
        private set

    private var lastMeta: FrameMeta? = null
    private var lastFrame: Frame? = null
    private var lastT = 0L
    private var lookId = 0
    private var lastLookMs = Long.MIN_VALUE / 2
    private var looksTotal = 0
    private val lookTimes = ArrayDeque<Long>()
    private var aiLast = 0L
    private var aiSum = 0L
    private var aiN = 0
    private var framesSeen = 0
    private var framesAnalysed = 0
    private var framesSkipped = 0
    private var framesSkippedBusy = 0
    private var framesSkippedPaused = 0
    private var activeCovers = 0

    fun onEvent(e: UiEvent) {
        synchronized(lock) {
            lastT = maxOf(lastT, e.tMs)
            pipeline.onEvent(e)
            val p = e.packageName
            val pause = e.type == "screenOff" || (e.type == "windowChanged" && p != null && p in skipApps)
            val resume = e.type == "screenOn" || (e.type == "windowChanged" && p != null && p !in skipApps)
            if (pause && !paused) {
                paused = true
                val m = lastMeta
                val pl =
                    plan(emptyList(), e.tMs, m?.frameId ?: 0, m?.screenWidth ?: 0, m?.screenHeight ?: 0, mode, "clear")
                emit(pl)
                log.write(linkedMapOf("kind" to "pause", "tMs" to e.tMs, "type" to e.type, "pkg" to p))
            } else if (resume) {
                paused = false
            }
            if (e.type == "scrolled" && !paused) overlay.shift(e.dx, e.dy, e.tMs)
        }
    }

    /** Injects a finding that arrived outside a look (replay). */
    fun inject(f: Record) {
        synchronized(lock) { pipeline.enqueue(f) }
    }

    fun offer(f: Frame) {
        synchronized(lock) { framesSeen++ }
        if (slot.getAndSet(f) != null) synchronized(lock) { framesSkipped++ }
    }

    fun pump() {
        val f = slot.getAndSet(null) ?: return
        synchronized(lock) { step(f) }
    }

    private fun emit(pl: Record) {
        lastPlan = pl
        activeCovers = (pl["masks"] as? List<*>)?.size ?: 0
        overlay.submit(pl)
        log.write(linkedMapOf("kind" to "plan", "tMs" to pl["tMs"], "plan" to pl))
    }

    private fun step(f: Frame) {
        lastMeta = f.meta
        lastFrame = f
        lastT = maxOf(lastT, f.meta.tMs)
        if (paused) {
            framesSkippedPaused++
            return
        }
        framesAnalysed++
        handle(f, pipeline.step(f.thumb, f.meta))
        if (idleLookMs > 0 && !worker.busy && f.meta.tMs - lastLookMs >= idleLookMs) {
            val whole = mapOf("x" to 0, "y" to 0, "w" to f.meta.screenWidth, "h" to f.meta.screenHeight)
            startLook(f, linkedMapOf("look" to true, "rect" to whole, "reason" to "idle"))
        }
    }

    /**
     * A still screen sends no further frame, so findings would never reach a plan. Re-step the brain on the last
     * frame at look-start + AI time (no motion, same thumb). Also fires the confirm look for tentative tracks.
     */
    private fun settle(tMs: Long) {
        val f = lastFrame ?: return
        if (paused) return
        lastT = maxOf(lastT, tMs)
        handle(f, pipeline.replan(f.meta, tMs))
    }

    private fun handle(f: Frame, records: List<Record>) {
        for (r in records) {
            when (r["kind"]) {
                "look" -> if (r["look"] == true) startLook(f, r)

                "maskPlan" -> {
                    @Suppress("UNCHECKED_CAST")
                    emit(r["plan"] as Record)
                }
            }
        }
    }

    private fun startLook(f: Frame, look: Record) {
        if (worker.busy) {
            framesSkippedBusy++
            return
        }
        val id = ++lookId
        lastLookMs = f.meta.tMs

        @Suppress("UNCHECKED_CAST")
        val lr = look["rect"] as Map<String, Number>
        val rect =
            Rect(lr.getValue("x").toInt(), lr.getValue("y").toInt(), lr.getValue("w").toInt(), lr.getValue("h").toInt())
        log.write(
            linkedMapOf(
                "kind" to "look",
                "tMs" to f.meta.tMs,
                "frameId" to f.meta.frameId,
                "lookId" to id,
                "rect" to rect.toMap()
            )
        )
        val nodes = layout()
        log.write(
            linkedMapOf(
                "kind" to "layout",
                "lookId" to id,
                "nodes" to nodes.filter { it.kind == "image" || it.kind == "video" || it.kind == "post" }.take(24)
                    .map { linkedMapOf("k" to it.kind, "rect" to it.rect.toMap()) }
            )
        )
        worker.submit(
            { runLanesIsolated(lanes, LookInput(id, f, rect, nodes, mode), log) },
            { found, aiMs -> done(found, aiMs, f.meta.tMs) }
        )
    }

    private fun done(found: List<Finding>, aiMs: Long, tMs: Long) {
        synchronized(lock) {
            for (x in found) {
                pipeline.enqueue(x)
                log.write(
                    linkedMapOf(
                        "kind" to "finding",
                        "findingId" to x.findingId,
                        "conceptId" to x.conceptId,
                        "lane" to x.lane,
                        "decision" to x.decision,
                        "p" to Math.round(x.probability * 1000) / 1000.0,
                        "rect" to x.rect.toMap()
                    )
                )
            }
            looksTotal++
            lookTimes.addLast(tMs)
            while (lookTimes.isNotEmpty() && lookTimes.first < tMs - 5000) lookTimes.removeFirst()
            aiLast = aiMs
            aiSum += aiMs
            aiN++
            if (autoSettle && found.isNotEmpty() && slot.get() == null) settle(tMs + maxOf(aiMs, 1L))
            val s =
                linkedMapOf<String, Any?>(
                    "kind" to "stats", "tMs" to lastT, "mode" to mode, "looksTotal" to looksTotal,
                    "looksPerSecond" to lookTimes.size / 5.0, "aiMsLast" to aiLast,
                    "aiMsMean" to aiSum.toDouble() / aiN, "cacheHits" to (counters.m["cacheHits"] ?: 0L),
                    "activeCovers" to activeCovers, "framesSeen" to framesSeen, "framesAnalysed" to framesAnalysed,
                    "framesSkipped" to framesSkipped, "framesSkippedBusy" to framesSkippedBusy,
                    "framesSkippedPaused" to framesSkippedPaused, "paused" to paused, "counters" to HashMap(counters.m)
                )
            stats.publish(s)
            log.write(s)
        }
    }
}
