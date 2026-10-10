package com.veil.brain.gate

import com.veil.brain.contract.FrameMeta
import com.veil.brain.contract.Record
import com.veil.brain.contract.Rect
import com.veil.brain.contract.UiEvent

interface Gate {
    var busyUntil: Long
    var rateMul: Int
    fun onEvent(event: UiEvent): List<Record>
    fun onThumb(thumb: ByteArray, frame: FrameMeta): Pair<Record, Record>
}

@Suppress("UNCHECKED_CAST")
object Gatekeeper {
    fun create(mode: String, paramsJson: String, lookMs: Int): Gate {
        val root = MiniJson(paramsJson).parse() as Map<String, Any?>
        val m = (root["modes"] as Map<String, Any?>)[mode] as Map<String, Any?>
        val c = m["change"] as Map<String, Any?>
        val s = m["sched"] as Map<String, Any?>

        fun ci(k: String, d: Int) = (c[k] as? Number)?.toInt() ?: d
        fun si(k: String, d: Int) = (s[k] as? Number)?.toInt() ?: d
        val cp = ChangeParams(
            ci("ignore_top_rows", 2),
            ci("ignore_bottom_rows", 2),
            ci("tile_level", 12),
            ci("cut_tile_level", 40),
            ci("cut_pct", 60),
            ci("cut_global", 30),
            ci("cut_min_tiles", 8),
            ci("own_mask", 0) == 1
        )
        val skip = (s["skip_packages"] as? List<String>) ?: emptyList()
        val mp = ModeParams(
            si("rate", 1), si("checkup_ms", 5000), si("min_immediate_gap_ms", 150), si("hot_ms", 3000),
            si("hot_rate_mul", 2), si("throttle_div", 2), si("burst_gap_ms", 150), si("deadline_ms", 200), skip
        )
        return GatekeeperPipeline(cp, mp, lookMs)
    }
}

class GatekeeperPipeline(private val cp: ChangeParams, private val mp: ModeParams, private val lookMs: Int) : Gate {
    override var busyUntil: Long = -1_000_000_000L
    override var rateMul: Int = 1
    private var state = SchedState()
    private var ref: ByteArray? = null
    private var refOwn: BooleanArray? = null
    private var dySinceRef = 0
    private var pkg: String? = null
    private val buf = ArrayList<UiEvent>()

    override fun onEvent(event: UiEvent): List<Record> {
        buf.add(event)
        return emptyList()
    }

    private fun fold(): Triple<Int, Boolean, Boolean?> {
        var dy = 0
        var wc = false
        var screen: Boolean? = null
        for (e in buf) {
            val p = e.packageName
            when {
                e.type == "scrolled" -> dy += e.dy
                e.type == "windowChanged" && p != null && p != pkg -> wc = true
                e.type == "screenOff" -> screen = false
                e.type == "screenOn" -> screen = true
            }
            if (p != null) pkg = p
        }
        buf.clear()
        return Triple(dy, wc, screen)
    }

    override fun onThumb(thumb: ByteArray, frame: FrameMeta): Pair<Record, Record> {
        val t = frame.tMs
        val (dy, wc, screen) = fold()
        dySinceRef += dy
        val shift = Change.shiftRows(dySinceRef, frame.width, frame.height, frame.screenWidth)
        // Pixels under our own covers (now, or when the reference was taken) are not real screen change.
        val curOwn = if (cp.ownMask) ownThumbMask(frame.ownOverlay, frame.screenWidth, frame.screenHeight) else null
        val res = Change.detect(thumb, ref, shift, cp, curOwn, refOwn)
        var revealed: Rect? = null
        val rr = res.revealedRows
        if (rr != null) {
            var r0 = rr.first
            var r1 = rr.second
            if (r0 <= cp.ignoreTopRows) r0 = 0
            if (r1 >= THUMB_H - cp.ignoreBottomRows) r1 = THUMB_H
            revealed = Change.thumbBoxToScreen(intArrayOf(0, r0, THUMB_W, r1), frame)
        }
        val changed = res.changedBox?.let { Change.thumbBoxToScreen(it, frame) }
        val tick = Tick(
            tMs = t, frameId = frame.frameId, screenW = frame.screenWidth, screenH = frame.screenHeight,
            changedTiles = res.changedTiles, sceneCut = res.sceneCut, revealedRect = revealed,
            changedRect = changed, scrollDy = dy, windowChanged = wc, packageName = pkg,
            screenOn = screen, busy = t < busyUntil
        )
        val before = state.skipped
        val (ns, req) = Scheduler.step(state, tick, mp)
        state = ns
        if (req != null) {
            ref = thumb
            refOwn = curOwn
            dySinceRef = 0
            busyUntil = t + lookMs
        } else if (ref == null) {
            ref = thumb
            refOwn = curOwn
        }
        val change: Record = linkedMapOf(
            "kind" to "change",
            "frameId" to frame.frameId,
            "tMs" to t,
            "changedTiles" to res.changedTiles,
            "sceneCut" to res.sceneCut,
            "score" to res.score,
            "x" to linkedMapOf(
                "revealedRows" to res.revealedRows?.let { listOf(it.first, it.second) },
                "shiftRows" to res.shiftRows
            )
        )
        val x = linkedMapOf<String, Any?>("queue" to 0, "skipped" to state.skipped)
        val look = linkedMapOf<String, Any?>(
            "kind" to "look",
            "frameId" to frame.frameId,
            "tMs" to t,
            "look" to (req != null),
            "reason" to (req?.why ?: if (state.skipped > before) "busy" else "none"),
            "state" to state.phase,
            "x" to x
        )
        if (req != null) {
            look["rect"] = req.rect.toMap()
            x["deadlineMs"] = req.deadlineMs
        }
        return Pair(change, look)
    }
}
