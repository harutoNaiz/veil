package com.veil.conductor.regions

import com.veil.brain.cache.FingerprintCache
import com.veil.brain.contract.CompiledConcept
import com.veil.brain.contract.Finding
import com.veil.brain.contract.Rect
import com.veil.brain.judge.Guards
import com.veil.brain.judge.Judge
import com.veil.conductor.Concepts
import com.veil.conductor.Counters
import com.veil.conductor.Describer
import com.veil.conductor.Finder
import com.veil.conductor.Lane
import com.veil.conductor.LookInput
import com.veil.conductor.Piece
import com.veil.conductor.Source

/**
 * Pieces (layout nodes, finder boxes, tiles, crops, whole) are described and judged. Finder boxes use their own
 * fingerprint against concepts.finder when there are any; otherwise (variant C) they are described by the
 * Describer like every other piece and judged against concepts.describer. Hits are then tightened: a coarse
 * hit that contains a clearly smaller hit of the same concept gives way to it, so the cover is the object.
 */
class RegionLane(
    private val concepts: Concepts,
    private val describer: Describer,
    private val finder: Finder?,
    private val cache: FingerprintCache,
    private val counters: Counters,
    private val proposer: RegionProposer = RegionProposer(),
    private val maxFinderBoxes: Int = 20,
    /** Product limits (live app): no cover above this % of the screen, none with a side under this px. */
    private val maxCoverScreenPct: Int = 100,
    private val minCoverSidePx: Int = 0,
    /** Live app: only an object box or a reported image element may cause a cover (coarse tiles alone are noisy). */
    private val requireFine: Boolean = false,
    /** false = cover just the object (its own box), not the whole picture it sits in. */
    private val snapPictures: Boolean = true
) : Lane {
    override fun run(input: LookInput): List<Finding> {
        val ownFp = concepts.finder.isNotEmpty()
        val boxes = finder?.boxes(input.frame, input.rect).orEmpty().take(maxFinderBoxes)
        val pieces = proposer.propose(input, boxes.map { it.first })
        for (p in pieces) counters.add("pieces.${p.source.wire}")
        val tMs = input.frame.meta.tMs
        val vecs = HashMap<String, FloatArray>()
        val misses = ArrayList<Pair<Piece, Long>>()
        for (p in pieces) {
            if (ownFp && p.source == Source.FINDER) {
                vecs[p.id] = boxes[p.id.substring(1).toInt()].second
                continue
            }
            val h = Hashes.dhash64(input.frame, p.rect)
            val hit = cache.get(h, tMs)
            if (hit != null) {
                counters.add("cacheHits")
                vecs[p.id] = hit
            } else {
                counters.add("cacheMisses")
                misses.add(p to h)
            }
        }
        for (chunk in misses.chunked(16)) {
            val out = describer.describe(input.frame, chunk.map { it.first })
            counters.add("describerCalls")
            counters.m.merge("describerMaxBatch", chunk.size.toLong(), ::maxOf)
            chunk.forEachIndexed { i, (p, h) ->
                vecs[p.id] = out[i]
                cache.put(h, out[i], tMs)
            }
        }
        val hits = ArrayList<Pair<Finding, Piece>>()
        val general = if (ownFp) pieces.filter { it.source != Source.FINDER } else pieces
        judgeAll(input, general, vecs, concepts.describer, "describer", hits, guard = true)
        if (ownFp) judgeAll(input, pieces.filter { it.source == Source.FINDER }, vecs, concepts.finder, "finder", hits)
        val sw = input.frame.meta.screenWidth.toLong()
        val sh = input.frame.meta.screenHeight.toLong()
        val tight = tighten(hits, sw * sh).also { counters.add("tightened", (hits.size - it.size).toLong()) }
        val fineIds = hits.filter { (_, p) -> p.source == Source.FINDER }.map { it.first.findingId }.toSet()
        val solidIds = fineIds + hits.filter { (_, p) ->
            p.source == Source.LAYOUT && area(p.rect) * 100 <= sw * sh * FINE_MAX_SCREEN_PCT
        }.map { it.first.findingId }
        // A cover is never most of the screen (the phone must stay usable) and never a tiny icon or avatar.
        val placed = if (snapPictures) snapToPictures(tight, fineIds, pieces, input, sw * sh) else tight
        return placed.filter { f ->
            f.decision != "hide" || f.layer == 1 ||
                (
                    (!requireFine || f.findingId in solidIds) &&
                        area(f.rect) * 100 <= sw * sh * maxCoverScreenPct &&
                        minOf(f.rect.w, f.rect.h) >= minCoverSidePx
                    )
        }
    }

    /**
     * Cover the picture, not the animal. A tight hide takes the rect of the picture it sits in: an image/video the
     * app reports (>= 60% inside it), else the picture's edges found in the pixels (grow until a flat gutter).
     * Coarse hides overlapping a snapped picture of the same concept are duplicates (they bridge two pictures).
     */
    private fun snapToPictures(
        fs: List<Finding>,
        fineIds: Set<String>,
        pieces: List<Piece>,
        input: LookInput,
        screenArea: Long
    ): List<Finding> {
        val images = pieces.filter {
            it.source == Source.LAYOUT && (it.kind == "image" || it.kind == "video") &&
                area(it.rect) * 100 <= screenArea * FINE_MAX_SCREEN_PCT
        }
        val pics = ArrayList<Finding>()
        val rest = ArrayList<Finding>()
        for (f in fs) {
            if (f.decision != "hide" || f.findingId !in fineIds) {
                rest.add(f)
                continue
            }
            val img = images.filter { inter(f.rect, it.rect) * 10 >= area(f.rect) * 6 }.minByOrNull { area(it.rect) }
            val r = img?.rect ?: PictureEdges.snap(input.frame, f.rect)
            if (pics.none { p ->
                    p.conceptId == f.conceptId && inter(p.rect, r) * 10 >= minOf(area(p.rect), area(r)) * 6
                }
            ) {
                pics.add(f.copy(rect = r))
            }
        }
        counters.add("snapped", pics.size.toLong())
        return pics + rest.filter { f ->
            f.decision != "hide" ||
                pics.none { p -> p.conceptId == f.conceptId && inter(f.rect, p.rect) * 10 >= area(f.rect) }
        }
    }

    private companion object {
        const val FINE_MAX_SCREEN_PCT = 35
        const val GROW = 0.15 // twin: guards.GROW
    }

    private fun area(r: Rect) = r.w.toLong() * r.h

    private fun inter(a: Rect, b: Rect): Long {
        val w = minOf(a.x + a.w, b.x + b.w) - maxOf(a.x, b.x)
        val h = minOf(a.y + a.h, b.y + b.h) - maxOf(a.y, b.y)
        return if (w <= 0 || h <= 0) 0L else w.toLong() * h
    }

    /**
     * Tight hides win (twin: guards.tighten). Fine hides are finder boxes and layout nodes up to 35% of the screen.
     * Any other hide of the same concept that is at least 1.5x larger than a fine hide it overlaps (>= 10% of the fine
     * hide's area) is not covered whole: it is clipped to each such fine hide grown by 15% per side (a detector box
     * often shows only part of the object). Without a fine hide the coarse piece stays as the fallback cover.
     * Non-hide findings pass through.
     */
    private fun tighten(hits: List<Pair<Finding, Piece>>, screenArea: Long): List<Finding> {
        fun hide(f: Finding) = f.decision == "hide"
        val fine = hits.filter { (f, p) ->
            hide(f) && (
                p.source == Source.FINDER ||
                    (p.source == Source.LAYOUT && area(p.rect) * 100 <= screenArea * FINE_MAX_SCREEN_PCT)
                )
        }
        val out = ArrayList<Finding>()
        for ((f, p) in hits) {
            val under = if (!hide(f) || p.source == Source.FINDER) {
                emptyList()
            } else {
                fine.filter { (g, q) ->
                    g.conceptId == f.conceptId && q !== p &&
                        area(p.rect) * 2 >= area(q.rect) * 3 &&
                        inter(p.rect, q.rect) * 10 >= area(q.rect)
                }
            }
            if (under.isEmpty()) {
                // Individual regions only: once tight boxes exist for this concept, a coarse hide that sits on none
                // of them is dropped (it would cover text and gaps). Without any tight box it stays as the fallback.
                val coarse = hide(f) && fine.none { it.second === p }
                if (coarse && fine.any { it.first.conceptId == f.conceptId }) continue
                out.add(f)
                continue
            }
            for ((_, q) in under) {
                val c = clipToGrown(p.rect, q.rect) ?: continue
                out.add(f.copy(findingId = "${f.findingId}~${q.id}".take(64), rect = c))
            }
        }
        return out
    }

    private fun clipToGrown(r: Rect, f: Rect): Rect? {
        val gx = Math.rint(f.w * GROW).toInt()
        val gy = Math.rint(f.h * GROW).toInt()
        val x0 = maxOf(r.x, f.x - gx)
        val y0 = maxOf(r.y, f.y - gy)
        val x1 = minOf(r.x + r.w, f.x + f.w + gx)
        val y1 = minOf(r.y + r.h, f.y + f.h + gy)
        return if (x1 <= x0 || y1 <= y0) null else Rect(x0, y0, x1 - x0, y1 - y0)
    }

    private fun judgeAll(
        input: LookInput,
        ps: List<Piece>,
        vecs: Map<String, FloatArray>,
        cs: List<CompiledConcept>,
        lane: String,
        out: MutableList<Pair<Finding, Piece>>,
        guard: Boolean = false
    ) {
        if (ps.isEmpty()) return
        val gp = ps.map { Guards.Piece(it.source.wire, it.rect) }
        val flat = if (guard) ps.map { Guards.isFlat(Hashes.lumaGrid(input.frame, it.rect)) } else null
        val norm = ps.map { p ->
            val v = vecs.getValue(p.id)
            val n = maxOf(Math.sqrt(v.sumOf { (it * it).toDouble() }), 1e-12)
            DoubleArray(v.size) { v[it] / n }
        }
        for (c in cs) {
            val verdicts = Judge.judge(norm, c, input.mode)
            val hide = if (guard) Guards.apply(gp, verdicts.map { it.decision == "hide" }, flat) else null
            verdicts.forEachIndexed { i, v ->
                if (v.decision == "leave") return@forEachIndexed
                if (hide != null && v.decision == "hide" && !hide[i]) return@forEachIndexed // guarded: not a hide
                val p = ps[i]
                out.add(
                    Finding(
                        findingId = "f$i-${p.id}".take(64),
                        frameId = input.frame.meta.frameId,
                        lookId = input.lookId,
                        tMs = input.frame.meta.tMs,
                        conceptId = c.conceptId,
                        layer = 2,
                        decision = v.decision,
                        probability = v.probability.coerceIn(0.0, 1.0),
                        rect = p.rect,
                        scope = "object",
                        lane = lane
                    ) to p
                )
            }
        }
    }
}
