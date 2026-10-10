package com.veil.brain.cover

import com.veil.brain.contract.Record
import com.veil.brain.contract.Rect

data class PlanParams(val padPct: Int, val dropShortPx: Int, val layer2Style: String, val maxMasks: Int = 24)

val PLAN_MODES =
    mapOf(
        "light" to PlanParams(4, 32, "blur"),
        "balanced" to PlanParams(6, 0, "blur"),
        "strict" to PlanParams(10, 0, "solid")
    )

private class Mask(val layer: Int, val rect: Rect, val conceptIds: List<String>, val trackIds: List<Int>)

private fun pad(r: Rect, pct: Int, sw: Int, sh: Int): Rect? {
    val p = minOf(r.w, r.h) * pct / 100
    val x0 = maxOf(0, r.x - p)
    val y0 = maxOf(0, r.y - p)
    val x1 = minOf(sw, r.x + r.w + p)
    val y1 = minOf(sh, r.y + r.h + p)
    return if (x1 <= x0 || y1 <= y0) null else Rect(x0, y0, x1 - x0, y1 - y0)
}

private fun interArea(a: Rect, b: Rect): Long {
    val w = minOf(a.x + a.w, b.x + b.w) - maxOf(a.x, b.x)
    val h = minOf(a.y + a.h, b.y + b.h) - maxOf(a.y, b.y)
    return if (w <= 0 || h <= 0) 0L else w.toLong() * h
}

/**
 * Two padded masks are one object only when they genuinely overlap: the intersection is at least [MERGE_OVERLAP_PCT]
 * of the smaller mask, and their union box adds at most [MERGE_INFLATE_PCT] percent over the area of their content
 * (a + b - inter). Touching or lightly overlapping neighbours (a dense photo grid, padding makes them touch) stay
 * separate, so merging can never chain a grid into one slab covering text and gaps.
 */
const val MERGE_OVERLAP_PCT = 50
const val MERGE_INFLATE_PCT = 150

private fun meets(a: Rect, b: Rect): Boolean {
    val i = interArea(a, b)
    if (i == 0L) return false
    val aa = a.w.toLong() * a.h
    val ba = b.w.toLong() * b.h
    if (i * 100 < minOf(aa, ba) * MERGE_OVERLAP_PCT) return false
    val u = union(a, b)
    return u.w.toLong() * u.h * 100 <= (aa + ba - i) * MERGE_INFLATE_PCT
}

private fun union(a: Rect, b: Rect): Rect {
    val x0 = minOf(a.x, b.x)
    val y0 = minOf(a.y, b.y)
    val x1 = maxOf(a.x + a.w, b.x + b.w)
    val y1 = maxOf(a.y + a.h, b.y + b.h)
    return Rect(x0, y0, x1 - x0, y1 - y0)
}

private fun join(a: Mask, b: Mask) = Mask(
    a.layer,
    union(a.rect, b.rect),
    (a.conceptIds + b.conceptIds).toSortedSet().toList(),
    (a.trackIds + b.trackIds).toSortedSet().toList()
)

private val maskOrder: Comparator<Mask> =
    compareBy<Mask>({ it.layer }, { it.rect.y }, { it.rect.x }, { it.rect.w }, { it.rect.h })

private fun merge(masks: List<Mask>): List<Mask> {
    val cur = masks.sortedWith(maskOrder).toMutableList()
    var changed = true
    while (changed) {
        changed = false
        loop@ for (i in cur.indices) {
            for (j in i + 1 until cur.size) {
                if (cur[i].layer == cur[j].layer && meets(cur[i].rect, cur[j].rect)) {
                    cur[i] = join(cur[i], cur[j])
                    cur.removeAt(j)
                    changed = true
                    break@loop
                }
            }
        }
    }
    return cur.sortedWith(maskOrder)
}

private fun area(r: Rect) = r.w * r.h

private fun cap(masks: List<Mask>, limit: Int): List<Mask> {
    var cur = masks.toList()
    while (cur.size > limit) {
        var bc = 0
        var bi = -1
        var bj = -1
        for (i in cur.indices) {
            for (j in i + 1 until cur.size) {
                if (cur[i].layer != cur[j].layer) continue
                val cost = area(union(cur[i].rect, cur[j].rect)) - area(cur[i].rect) - area(cur[j].rect)
                if (bi < 0 || cost < bc) {
                    bc = cost
                    bi = i
                    bj = j
                }
            }
        }
        if (bi < 0) break
        val m = cur.toMutableList()
        m[bi] = join(m[bi], m[bj])
        m.removeAt(bj)
        cur = merge(m)
    }
    return cur
}

fun plan(
    tracks: List<Record>,
    tMs: Long,
    frameId: Int,
    screenW: Int,
    screenH: Int,
    mode: String,
    reason: String,
    labels: Boolean = false,
    solidOnly: Boolean = false
): Record {
    val p = PLAN_MODES.getValue(mode)
    val raw = ArrayList<Mask>()
    for (t in tracks.sortedBy { num(it["trackId"]) }) {
        if (t["state"] != "confirmed" || t["peeked"] == true) continue
        val rect = rectOf(t["rect"])
        val layer = num(t["layer"])
        if (layer != 1 && minOf(rect.w, rect.h) < p.dropShortPx) continue
        val padded = pad(rect, p.padPct, screenW, screenH) ?: continue
        raw.add(Mask(layer, padded, listOf(t["conceptId"] as String), listOf(num(t["trackId"]))))
    }
    val masks = cap(merge(raw), p.maxMasks)
    val out =
        masks.mapIndexed { i, m ->
            val style = if (m.layer == 1) {
                "solid"
            } else if (solidOnly) {
                "solid"
            } else {
                p.layer2Style
            }
            val d =
                linkedMapOf<String, Any?>(
                    "contractVersion" to "1.0",
                    "maskId" to i + 1,
                    "rect" to m.rect.toMap(),
                    "style" to style,
                    "layer" to m.layer,
                    "peekable" to (m.layer != 1),
                    "conceptIds" to m.conceptIds.take(8),
                    "trackIds" to m.trackIds.take(32)
                )
            if (labels) d["label"] = ("Hidden · " + m.conceptIds.joinToString(", ")).take(64)
            d
        }
    return linkedMapOf(
        "contractVersion" to "1.0",
        "planId" to frameId,
        "tMs" to tMs,
        "screenWidth" to screenW,
        "screenHeight" to screenH,
        "rotation" to 0,
        "masks" to out,
        "basedOnFrameId" to frameId,
        "reason" to reason
    )
}
