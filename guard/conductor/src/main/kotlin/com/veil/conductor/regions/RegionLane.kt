package com.veil.conductor.regions

import com.veil.brain.cache.FingerprintCache
import com.veil.brain.contract.CompiledConcept
import com.veil.brain.contract.Finding
import com.veil.brain.judge.Judge
import com.veil.conductor.Concepts
import com.veil.conductor.Counters
import com.veil.conductor.Describer
import com.veil.conductor.Finder
import com.veil.conductor.Lane
import com.veil.conductor.LookInput
import com.veil.conductor.Piece
import com.veil.conductor.Source

class RegionLane(
    private val concepts: Concepts,
    private val describer: Describer,
    private val finder: Finder?,
    private val cache: FingerprintCache,
    private val counters: Counters,
    private val proposer: RegionProposer = RegionProposer()
) : Lane {
    override fun run(input: LookInput): List<Finding> {
        val boxes = finder?.boxes(input.frame, input.rect).orEmpty()
        val pieces = proposer.propose(input, boxes.map { it.first })
        for (p in pieces) counters.add("pieces.${p.source.wire}")
        val tMs = input.frame.meta.tMs
        val vecs = HashMap<String, FloatArray>()
        val misses = ArrayList<Pair<Piece, Long>>()
        for (p in pieces) {
            if (p.source == Source.FINDER) {
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
        val findings = ArrayList<Finding>()
        val general = pieces.filter { it.source != Source.FINDER }
        judgeAll(input, general, vecs, concepts.describer, "describer", findings)
        judgeAll(input, pieces.filter { it.source == Source.FINDER }, vecs, concepts.finder, "finder", findings)
        return findings
    }

    private fun judgeAll(
        input: LookInput,
        ps: List<Piece>,
        vecs: Map<String, FloatArray>,
        cs: List<CompiledConcept>,
        lane: String,
        out: MutableList<Finding>
    ) {
        if (ps.isEmpty()) return
        val norm = ps.map { p ->
            val v = vecs.getValue(p.id)
            val n = maxOf(Math.sqrt(v.sumOf { (it * it).toDouble() }), 1e-12)
            DoubleArray(v.size) { v[it] / n }
        }
        for (c in cs) {
            Judge.judge(norm, c, input.mode).forEachIndexed { i, v ->
                if (v.decision == "leave") return@forEachIndexed
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
                    )
                )
            }
        }
    }
}
