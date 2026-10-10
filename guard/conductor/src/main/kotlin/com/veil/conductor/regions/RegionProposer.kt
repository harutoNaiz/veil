package com.veil.conductor.regions

import com.veil.brain.contract.Rect
import com.veil.brain.cover.iouPct
import com.veil.conductor.LookInput
import com.veil.conductor.Piece
import com.veil.conductor.Source

class RegionProposer(
    private val grid: Pair<Int, Int> = 3 to 6,
    private val overlap: Double = 0.25,
    private val tallCrops: Int = 3,
    /** Live app: page images smaller than this (icons, avatars, buttons) are not pieces. */
    private val minLayoutSidePx: Int = 0
) {
    private fun rnd(v: Double): Int = Math.rint(v).toInt()

    private fun rect(x: Double, y: Double, w: Double, h: Double, width: Int, height: Int): Rect {
        val x0 = maxOf(0, rnd(x))
        val y0 = maxOf(0, rnd(y))
        val x1 = minOf(width, rnd(x + w))
        val y1 = minOf(height, rnd(y + h))
        return Rect(x0, y0, maxOf(1, x1 - x0), maxOf(1, y1 - y0))
    }

    private fun overlapPct(a: Rect, b: Rect): Double {
        val w = minOf(a.x + a.w, b.x + b.w) - maxOf(a.x, b.x)
        val h = minOf(a.y + a.h, b.y + b.h) - maxOf(a.y, b.y)
        return if (w <= 0 || h <= 0) 0.0 else w.toDouble() * h / (a.w.toDouble() * a.h)
    }

    /** A big image/video node may span flat letterbox bars around the photo: cut them off so the piece is the photo. */
    private fun visible(input: LookInput, kind: String, r: Rect): Rect {
        val argb = input.frame.argb ?: return r
        if (kind == "post") return r
        val m = input.frame.meta
        if (r.w.toLong() * r.h * 5 < m.screenWidth.toLong() * m.screenHeight) return r
        return BarTrim.trim(argb, m.width, m.height, m.screenWidth, m.screenHeight, r)
    }

    fun propose(input: LookInput, finderBoxes: List<Rect>): List<Piece> {
        val look = input.lookId
        val out = ArrayList<Piece>()
        input.layout.forEachIndexed { i, n ->
            if ((n.kind == "image" || n.kind == "video" || n.kind == "post") &&
                minOf(n.rect.w, n.rect.h) >= minLayoutSidePx
            ) {
                out.add(Piece("L$i", visible(input, n.kind, n.rect), Source.LAYOUT, n.kind, look))
            }
        }
        finderBoxes.forEachIndexed { i, r -> out.add(Piece("f$i", r, Source.FINDER, "object", look)) }
        val width = input.frame.meta.screenWidth
        val height = input.frame.meta.screenHeight
        val portrait = height >= width
        val cols = if (portrait) grid.first else grid.second
        val rows = if (portrait) grid.second else grid.first
        val tw = width / (1 + (cols - 1) * (1 - overlap))
        val th = height / (1 + (rows - 1) * (1 - overlap))
        val extra = ArrayList<Piece>()
        for (r in 0 until rows) {
            for (c in 0 until cols) {
                val rc = rect(c * tw * (1 - overlap), r * th * (1 - overlap), tw, th, width, height)
                extra.add(Piece("t$r-$c", rc, Source.TILE, "unknown", look, "whole"))
            }
        }
        val side = minOf(width, height).toDouble()
        for (i in 0 until tallCrops) {
            val frac = if (tallCrops > 1) i.toDouble() / (tallCrops - 1) else 0.5
            val rc = if (portrait) {
                rect(0.0, frac * (height - side), side, side, width, height)
            } else {
                rect(frac * (width - side), 0.0, side, side, width, height)
            }
            extra.add(Piece("c$i", rc, Source.CROP, "unknown", look, "whole"))
        }
        extra.add(Piece("whole", Rect(0, 0, width, height), Source.WHOLE, "screen", look))
        out.addAll(extra.filter { overlapPct(it.rect, input.rect) >= 0.25 })
        val kept = ArrayList<Piece>()
        for (p in out) { // already in priority order layout > finder > tile > crop > whole
            if (kept.none { iouPct(it.rect, p.rect) >= 80 }) kept.add(p)
        }
        return kept
    }
}
