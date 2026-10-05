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
    private val layout: () -> List<LayoutNode>
) {
    private val pipeline = BrainPipeline(mode, paramsJson)
    private val lock = Any()
    private val slot = AtomicReference<Frame?>(null)

    @Volatile var paused = false
        private set

    @Volatile var lastPlan: Record? = null
        private set

    private var lastMeta: FrameMeta? = null
    private var lastT = 0L
    private var lookId = 0
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
        lastT = maxOf(lastT, f.meta.tMs)
        if (paused) {
            framesSkippedPaused++
            return
        }
        framesAnalysed++
        for (r in pipeline.step(f.thumb, f.meta)) {
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
        worker.submit(
            { lanes.flatMap { it.run(LookInput(id, f, rect, nodes, mode)) } },
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
                        "lane" to x.lane
                    )
                )
            }
            looksTotal++
            lookTimes.addLast(tMs)
            while (lookTimes.isNotEmpty() && lookTimes.first < tMs - 5000) lookTimes.removeFirst()
            aiLast = aiMs
            aiSum += aiMs
            aiN++
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
