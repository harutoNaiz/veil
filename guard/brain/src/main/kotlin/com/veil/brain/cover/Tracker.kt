package com.veil.brain.cover

import com.veil.brain.contract.Record
import com.veil.brain.contract.Rect

data class TrackParams(
    val confirmN: Int,
    val holdMs: Int,
    val maxHoldMs: Int,
    val parkMs: Int = 3000,
    val iouHidePct: Int = 30,
    val iouKeepPct: Int = 50,
    val selfCapturePct: Int = 80,
    /** A sighting with probability >= this (or lane "video" when <= 1.0) confirms at once; 2.0 = off. */
    val instantProb: Double = 2.0
)

val TRACK_MODES =
    mapOf(
        "light" to TrackParams(3, 800, 10000),
        "balanced" to TrackParams(2, 1500, 20000),
        "strict" to TrackParams(1, 3000, 30000)
    )

internal fun num(v: Any?): Int = (v as Number).toInt()

internal fun rectOf(m: Any?): Rect {
    @Suppress("UNCHECKED_CAST")
    val r = m as Map<String, Any?>
    return Rect(num(r["x"]), num(r["y"]), num(r["w"]), num(r["h"]))
}

private fun inter(a: Rect, b: Rect): Int {
    val w = minOf(a.x + a.w, b.x + b.w) - maxOf(a.x, b.x)
    val h = minOf(a.y + a.h, b.y + b.h) - maxOf(a.y, b.y)
    return if (w <= 0 || h <= 0) 0 else w * h
}

fun iouPct(a: Rect, b: Rect): Int {
    val i = inter(a, b)
    if (i == 0) return 0
    val union = a.w * a.h + b.w * b.h - i
    return i * 100 / union
}

fun coveredPct(r: Rect, covers: List<Rect>): Int {
    val area = r.w * r.h
    if (area <= 0) return 0
    val raster = BooleanArray(area)
    for (c in covers) {
        val x0 = maxOf(c.x, r.x) - r.x
        val y0 = maxOf(c.y, r.y) - r.y
        val x1 = minOf(c.x + c.w, r.x + r.w) - r.x
        val y1 = minOf(c.y + c.h, r.y + r.h) - r.y
        if (x1 > x0 && y1 > y0) {
            for (y in y0 until y1) for (x in x0 until x1) raster[y * r.w + x] = true
        }
    }
    return raster.count { it } * 100 / area
}

class Tr(val trackId: Int, f: Record, t: Long) {
    val conceptId = f["conceptId"] as String
    val layer = num(f["layer"])
    val scope = (f["scope"] as String?) ?: "object"
    val firstSeen = t
    var sightings = 0
    var state = "tentative"
    var prevState = "tentative"
    var parkedUntil: Long? = null
    var peeked = false
    var cut = false
    var rect = rectOf(f["rect"])
    var lastSeen = t
    var holdUntil = t
    var maxHoldUntil = t
    var findingId: String? = null
    var pct = 0
}

class Tracker(
    mode: String = "balanced",
    private var screenW: Int = 720,
    private var screenH: Int = 1600,
    private val rule: Boolean = true,
    private val p: TrackParams = TRACK_MODES.getValue(mode)
) {
    var tracks: List<Tr> = emptyList()
    private var nextId = 1
    private var dy = 0

    /** Real screen size from the frames (the 720x1600 default is the test tapes' size). */
    fun resize(w: Int, h: Int) {
        if (w > 0 && h > 0) {
            screenW = w
            screenH = h
        }
    }

    fun onScroll(d: Int) {
        for (tr in tracks) tr.rect = tr.rect.copy(y = tr.rect.y + d)
        dy += d
    }

    private fun sight(tr: Tr, f: Record, t: Long) {
        tr.sightings++
        tr.rect = rectOf(f["rect"])
        tr.lastSeen = t
        tr.holdUntil = t + p.holdMs
        tr.maxHoldUntil = t + p.maxHoldMs
        tr.findingId = f["findingId"] as String?
        tr.cut = false
        tr.parkedUntil = null
        val instant = p.instantProb <= 1.0 &&
            (((f["probability"] as? Number)?.toDouble() ?: 0.0) >= p.instantProb || f["lane"] == "video")
        tr.state = if (tr.layer == 1 || tr.sightings >= p.confirmN || instant) "confirmed" else "tentative"
    }

    private fun best(f: Record, used: Set<Int>, minPct: Int): Tr? {
        var best: Tr? = null
        var bestV = 0
        val fr = rectOf(f["rect"])
        for (tr in tracks) {
            if (tr.trackId in used || tr.conceptId != f["conceptId"]) continue
            val v = iouPct(tr.rect, fr)
            if (v < minPct) continue
            if (best == null || v > bestV || (v == bestV && tr.trackId < best.trackId)) {
                best = tr
                bestV = v
            }
        }
        return best
    }

    private val findingOrder: Comparator<Record> =
        compareBy<Record>({
            num(it["layer"])
        }, { it["conceptId"] as String }, { rectOf(it["rect"]).y }, { rectOf(it["rect"]).x })
            .thenBy { rectOf(it["rect"]).w }
            .thenBy { rectOf(it["rect"]).h }
            .thenBy { (it["findingId"] as String?) ?: "" }

    fun onFindings(findings: List<Record>, t: Long) {
        val used = HashSet<Int>()
        for (f in findings.filter { it["decision"] == "hide" }.sortedWith(findingOrder)) {
            var tr = best(f, used, p.iouHidePct)
            if (tr == null) {
                tr = Tr(nextId++, f, t)
                tracks = tracks + tr
            }
            used.add(tr.trackId)
            sight(tr, f, t)
        }
        for (f in findings.filter { it["decision"] == "nearMiss" }.sortedWith(findingOrder)) {
            val tr = best(f, used, p.iouKeepPct)
            if (tr != null) {
                used.add(tr.trackId)
                tr.holdUntil = t + p.holdMs
            }
        }
    }

    fun clear() {
        tracks = emptyList()
    }

    private fun onScreen(r: Rect) = inter(r, Rect(0, 0, screenW, screenH)) > 0

    fun tick(t: Long, ownCoversIn: List<Rect>): List<Record> {
        val covers = ownCoversIn.map { it.copy(y = it.y + dy) }
        dy = 0
        val keep = ArrayList<Tr>()
        for (tr in tracks.sortedBy { it.trackId }) {
            if (!onScreen(tr.rect)) {
                if (tr.state != "parked") {
                    tr.prevState = tr.state
                    tr.state = "parked"
                    tr.parkedUntil = t + p.parkMs
                }
                val pu = tr.parkedUntil
                if (pu != null && t >= pu) continue
                keep.add(tr)
                continue
            }
            if (tr.state == "parked") {
                tr.state = tr.prevState
                tr.parkedUntil = null
                tr.holdUntil = maxOf(tr.holdUntil, t + p.holdMs)
            }
            tr.pct = coveredPct(tr.rect, covers)
            if (t > tr.holdUntil) {
                val alive = rule && tr.pct >= p.selfCapturePct && !tr.cut && t < tr.maxHoldUntil
                if (!alive) continue
            }
            keep.add(tr)
        }
        tracks = keep
        return keep.map { tr ->
            val d =
                linkedMapOf<String, Any?>(
                    "contractVersion" to "1.0",
                    "trackId" to tr.trackId,
                    "conceptId" to tr.conceptId,
                    "layer" to tr.layer,
                    "rect" to tr.rect.toMap(),
                    "state" to tr.state,
                    "sightings" to tr.sightings,
                    "firstSeenMs" to tr.firstSeen,
                    "lastSeenMs" to tr.lastSeen,
                    "holdUntilMs" to tr.holdUntil,
                    "maxHoldUntilMs" to tr.maxHoldUntil,
                    "selfCaptureFraction" to tr.pct / 100.0,
                    "peeked" to tr.peeked,
                    "scope" to tr.scope
                )
            tr.parkedUntil?.let { d["parkedUntilMs"] = it }
            tr.findingId?.let { d["lastFindingId"] = it }
            d
        }
    }
}
