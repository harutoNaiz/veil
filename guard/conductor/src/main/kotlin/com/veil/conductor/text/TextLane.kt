package com.veil.conductor.text

import com.veil.brain.contract.Finding
import com.veil.brain.contract.Rect
import com.veil.conductor.Concepts
import com.veil.conductor.Counters
import com.veil.conductor.Lane
import com.veil.conductor.LayoutNode
import com.veil.conductor.LookInput
import com.veil.conductor.Ocr
import com.veil.conductor.TextClassifier

private const val WB = "\\b"

class TextLane(
    private val concepts: Concepts,
    private val tox: TextClassifier?,
    private val ocr: Ocr?,
    private val counters: Counters,
    private val toxThr: Map<String, Double> = mapOf("light" to 0.7, "balanced" to 0.5, "strict" to 0.35)
) : Lane {
    private val seen = object : LinkedHashMap<String, Double>(256, 0.75f, true) {
        override fun removeEldestEntry(e: MutableMap.MutableEntry<String, Double>) = size > 2000
    }
    private val rules = concepts.keywords.mapValues { (_, ws) ->
        ws.map { Regex(WB + Regex.escape(it.lowercase()) + WB) }
    }

    private fun norm(s: String) = s.lowercase().map {
        if (it.isWhitespace()) ' ' else it
    }.joinToString("").split(' ').filter { it.isNotEmpty() }.joinToString(" ")

    private fun inside(a: Rect, b: Rect) = a.x >= b.x && a.y >= b.y && a.x + a.w <= b.x + b.w && a.y + a.h <= b.y + b.h

    override fun run(input: LookInput): List<Finding> {
        val cands = ArrayList<Pair<LayoutNode, String>>()
        for (n in input.layout.filter { it.kind == "text" }) n.text?.let { cands.add(n to it) }
        if (ocr != null) {
            for (n in input.layout.filter { it.kind == "image" }.sortedByDescending { it.rect.w * it.rect.h }.take(4)) {
                counters.add("ocrCalls")
                ocr.read(input.frame, n.rect)?.let { cands.add(n to it) }
            }
        }
        val posts = input.layout.filter { it.kind == "post" }
        val thr = toxThr[input.mode] ?: 0.5
        val m = input.frame.meta
        val out = ArrayList<Finding>()
        for ((node, raw) in cands) {
            val t = norm(raw)
            if (t.isEmpty()) continue
            counters.add("textSeen")
            var concept: String? = null
            var p = 1.0
            for ((cid, res) in rules) {
                if (res.any { it.containsMatchIn(t) }) {
                    concept = cid
                    break
                }
            }
            if (concept == null && tox != null) {
                val s = seen[t] ?: tox.toxicity(t).also {
                    counters.add("toxicityCalls")
                    seen[t] = it
                }
                if (s >= thr) {
                    concept = "text.toxic"
                    p = s
                }
            }
            if (concept == null) continue
            val rect =
                posts.filter { inside(node.rect, it.rect) }.minByOrNull { it.rect.w * it.rect.h }?.rect ?: node.rect
            out.add(
                Finding(
                    "tx-${input.lookId}-${out.size}", m.frameId, input.lookId, m.tMs, concept, 2, "hide", p,
                    rect, "post", "text"
                )
            )
        }
        return out
    }
}
