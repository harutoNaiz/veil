package com.veil.brain.motion

import com.veil.brain.contract.Finding
import com.veil.brain.contract.FrameMeta
import com.veil.brain.contract.Record
import com.veil.brain.contract.Rect
import com.veil.brain.contract.UiEvent
import com.veil.brain.cover.Tracker
import com.veil.brain.cover.num
import com.veil.brain.cover.plan
import com.veil.brain.cover.rectOf
import com.veil.brain.gate.Gate
import com.veil.brain.gate.Gatekeeper

private const val NEVER = -1_000_000_000L

class BrainPipeline(
    private val mode: String,
    paramsJson: String,
    private val gate: Gate = Gatekeeper.create(mode, paramsJson, 100),
    private val latencyMs: Int = 100
) {
    private val tracker = Tracker(mode)
    private var inbox = ArrayList<Record>()
    private var cumDy = 0
    private val cumAt = HashMap<Int, Int>()
    private var lastStart = NEVER
    private var pkg: String? = null
    private var scrolled = false
    private var appChg = false
    private var prevIds: Set<Int> = emptySet()
    private var prevReason = "clear"
    private var first = true

    fun onEvent(e: UiEvent): List<Record> {
        gate.onEvent(e)
        val p = e.packageName
        when {
            e.type == "scrolled" -> {
                tracker.onScroll(e.dy)
                cumDy += e.dy
                scrolled = true
            }

            e.type == "windowChanged" && p != null && p != pkg -> {
                tracker.clear()
                appChg = true
            }

            e.type == "screenOff" -> {
                tracker.clear()
                appChg = true
            }
        }
        if (p != null) pkg = p
        return emptyList()
    }

    fun enqueue(f: Record) {
        inbox.add(f)
    }

    fun enqueue(f: Finding) {
        enqueue(
            linkedMapOf<String, Any?>(
                "findingId" to f.findingId,
                "frameId" to f.frameId,
                "lookId" to f.lookId,
                "tMs" to f.tMs,
                "conceptId" to f.conceptId,
                "layer" to f.layer,
                "decision" to f.decision,
                "probability" to f.probability,
                "rect" to f.rect.toMap(),
                "scope" to f.scope,
                "lane" to f.lane
            )
        )
    }

    private fun confirmRect(frame: FrameMeta): Rect? {
        val tent = tracker.tracks.filter { it.state == "tentative" }
        if (tent.isEmpty()) return null
        val x0 = maxOf(0, tent.minOf { it.rect.x } - 20)
        val y0 = maxOf(0, tent.minOf { it.rect.y } - 20)
        val x1 = minOf(frame.screenWidth, tent.maxOf { it.rect.x + it.rect.w } + 20)
        val y1 = minOf(frame.screenHeight, tent.maxOf { it.rect.y + it.rect.h } + 20)
        return if (x1 <= x0 || y1 <= y0) null else Rect(x0, y0, x1 - x0, y1 - y0)
    }

    fun step(thumb: ByteArray, frame: FrameMeta): List<Record> {
        val t = frame.tMs
        val fid = frame.frameId
        cumAt[fid] = cumDy
        val (change, look0) = gate.onThumb(thumb, frame)
        if (change["sceneCut"] == true) tracker.clear()
        val rect = confirmRect(frame)
        val fresh = tracker.tracks.any { it.state == "tentative" && it.lastSeen > lastStart }
        var look: Record = look0
        if (look["look"] != true) {
            if (rect != null && fresh && t >= gate.busyUntil) {
                @Suppress("UNCHECKED_CAST")
                val x = look["x"] as Map<String, Any?>
                look =
                    look +
                    mapOf(
                        "look" to true,
                        "reason" to "periodic",
                        "rect" to rect.toMap(),
                        "x" to (x + ("confirm" to true))
                    )
                gate.busyUntil = t + latencyMs
            }
        } else if (rect != null) {
            val a = rectOf(look["rect"])
            val x0 = minOf(a.x, rect.x)
            val y0 = minOf(a.y, rect.y)
            val x1 = maxOf(a.x + a.w, rect.x + rect.w)
            val y1 = maxOf(a.y + a.h, rect.y + rect.h)
            look = look + ("rect" to Rect(x0, y0, x1 - x0, y1 - y0).toMap())
        }
        if (look["look"] == true) lastStart = t
        val due = inbox
        inbox = ArrayList()
        val shifted =
            due.map { f ->
                val r = rectOf(f["rect"])
                val c = cumAt[num(f["frameId"])] ?: cumDy
                f + ("rect" to r.copy(y = r.y + cumDy - c).toMap())
            }
        tracker.onFindings(shifted, t)
        val tracks = tracker.tick(t, frame.ownOverlay)
        val ids = tracks.map { num(it["trackId"]) }.toSet()
        val reason =
            when {
                appChg -> "appChange"
                look["look"] == true || due.isNotEmpty() -> "look"
                scrolled -> "scroll"
                (prevIds - ids).isNotEmpty() -> "expire"
                tracks.isEmpty() || first -> "clear"
                else -> prevReason
            }
        prevIds = ids
        prevReason = reason
        first = false
        scrolled = false
        appChg = false
        val pl = plan(tracks, t, fid, frame.screenWidth, frame.screenHeight, mode, reason)
        return listOf(
            change,
            look,
            linkedMapOf("kind" to "tracks", "tMs" to t, "frameId" to fid, "tracks" to tracks),
            linkedMapOf("kind" to "maskPlan", "tMs" to t, "frameId" to fid, "plan" to pl)
        )
    }
}
