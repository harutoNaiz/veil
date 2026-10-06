package com.veil.teacher.autocal

import com.veil.brain.contract.AutoRule
import com.veil.brain.contract.AutoTerm
import com.veil.brain.contract.CompiledConcept
import com.veil.brain.contract.Embedding
import com.veil.teacher.Teacher
import com.veil.teacher.TextEncoder

/** Port of workshop/twin/autocal.py (null-quantile-v2). Every constant is global; nothing per word. */
object AutoCal {
    val TEMPLATES = listOf(
        "a photo of a {w}",
        "a {w}",
        "a close-up of a {w}",
        "a {w} in a meme",
        "a drawing of a {w}"
    )
    val MODES = listOf("light", "balanced", "strict")
    val Q_PER_MILLE = mapOf("light" to 999, "balanced" to 995, "strict" to 980)
    const val K_COMPETITORS = 8
    const val N_CHIPS = 6
    const val AUTO_MARGIN = 0.0
    private const val SPACE = "siglip2-base-p16-224"
    private const val MODEL = "siglip2-base-text"

    fun collapse(w: String) = w.trim().lowercase().split(Regex("\\s+")).filter { it.isNotEmpty() }.joinToString(" ")

    fun l2(v: DoubleArray): DoubleArray {
        var s = 0.0
        for (x in v) s += x * x
        val n = Math.sqrt(s)
        return if (n > 0) DoubleArray(v.size) { v[it] / n } else v
    }

    const val RULE = "null-quantile-v2"

    fun direction(e: DoubleArray, center: DoubleArray): DoubleArray = l2(DoubleArray(e.size) { e[it] - center[it] })

    fun dot(a: DoubleArray, b: DoubleArray): Double {
        var s = 0.0
        for (i in a.indices) s += a[i] * b[i]
        return s
    }

    /** Integer quantile index over the ascending null scores. */
    fun quantile(sortedAsc: DoubleArray, perMille: Int): Double {
        val n = sortedAsc.size
        val k = ((perMille * n + 999) / 1000 - 1).coerceIn(0, n - 1)
        return sortedAsc[k]
    }

    fun thresholds(e: DoubleArray, bank: BankFile, excl: Set<Int>): DoubleArray {
        val mask = bank.excludedMask(excl)
        val sc = bank.scores(e)
        val d = sc.filterIndexed { i, _ -> !mask[i] }.toDoubleArray().also { it.sort() }
        return DoubleArray(3) { quantile(d, Q_PER_MILLE.getValue(MODES[it])) }
    }

    fun ensemble(word: String, enc: TextEncoder): DoubleArray {
        val w = Teacher.singular(collapse(word))
        val vs = enc.encode(TEMPLATES.map { it.replace("{w}", w) })
            .map { l2(DoubleArray(it.size) { i -> it[i].toDouble() }) }
        val m = DoubleArray(vs[0].size) { i -> vs.sumOf { it[i] } / vs.size }
        return l2(m)
    }

    private fun term(name: String, v: DoubleArray, thr: Map<String, Double>, enc: TextEncoder?): AutoTerm {
        val f16 = Teacher.encodeF16(FloatArray(v.size) { v[it].toFloat() })
        val raw = linkedMapOf<String, Any?>(
            "contractVersion" to "1.0",
            "spaceId" to (enc?.spaceId ?: SPACE),
            "modelId" to (enc?.textModelId ?: MODEL),
            "dim" to v.size,
            "vectorF16" to f16,
            "kind" to "text",
            "text" to name.take(500)
        )
        return AutoTerm(name, Embedding(v.size, f16, raw), thr)
    }

    private fun thrMap(t: DoubleArray) = linkedMapOf("light" to t[0], "balanced" to t[1], "strict" to t[2])

    private fun termMap(t: AutoTerm) = mapOf(
        "term" to t.term,
        "embedding" to t.embedding.raw,
        "thresholds" to t.thresholds
    )

    /** Returns (cc, chips). [enc] is needed only for out-of-vocabulary words. */
    fun compileAuto(
        word: String,
        alsoHide: List<String>,
        enc: TextEncoder?,
        bank: BankFile,
        vocab: VocabFile
    ): Pair<CompiledConcept, List<String>> {
        val text = collapse(word)
        val idx = vocab.lookup(text)
        val e: DoubleArray
        val d: DoubleArray
        val thr: DoubleArray
        val excl: Set<Int>
        val rel: Set<Int>
        if (idx != null) {
            e = vocab.rows[idx]
            d = direction(e, vocab.center)
            thr = vocab.thr[idx]
            excl = vocab.entries[idx].excl
            rel = vocab.entries[idx].rel + idx
        } else {
            requireNotNull(enc) { "'$text' is not in the vocabulary and no text encoder is available" }
            e = ensemble(text, enc)
            d = direction(e, vocab.center)
            thr = thresholds(d, bank, emptySet())
            excl = emptySet()
            val sing = Teacher.singular(text)
            rel = vocab.entries.indices.filter { vocab.entries[it].name == sing }.toSet()
        }
        val excluded = bank.excludedMask(excl).count { it }
        val selected = alsoHide.mapNotNull { vocab.lookup(it) }.filter { it != idx }.distinct()
        val positives = (listOfNotNull(idx) + selected).toSet()
        fun rank(skip: Set<Int>) = vocab.entries.indices
            .filter { vocab.entries[it].kind == "noun" && it !in rel && it !in skip }
            .map { it to dot(e, vocab.rows[it]) }
            .sortedWith(compareBy({ -it.second }, { it.first }))
            .take(K_COMPETITORS)
            .map { it.first }
        val chips = rank(emptySet()).take(N_CHIPS).map { vocab.entries[it].name }
        val ranked = rank(positives)
        val ignores = vocab.entries.indices.filter { vocab.entries[it].kind == "ignore" }
        val pos = listOf(term(text, d, thrMap(thr), enc)) +
            selected.map {
                term(vocab.entries[it].name, direction(vocab.rows[it], vocab.center), thrMap(vocab.thr[it]), enc)
            }
        val comps = (ranked + ignores).map {
            term(
                vocab.entries[it].name,
                direction(vocab.rows[it], vocab.center),
                linkedMapOf("balanced" to vocab.thr[it][1]),
                enc
            )
        }
        val butNot = comps.dropLast(ignores.size)
        val ignore = comps.takeLast(ignores.size)
        val rawAuto = linkedMapOf<String, Any?>(
            "rule" to RULE,
            "bankId" to bank.bankId,
            "margin" to AUTO_MARGIN,
            "excluded" to excluded,
            "chips" to chips,
            "positives" to pos.map { termMap(it) },
            "competitors" to comps.map { termMap(it) }
        )
        val card = Teacher.conceptCard(text)
        val cid = card["conceptId"] as String
        val th = pos[0].thresholds.mapValues { it.value.coerceIn(0.0, 1.0) }
        val raw = linkedMapOf<String, Any?>(
            "contractVersion" to "1.0",
            "conceptId" to cid,
            "spaceId" to (enc?.spaceId ?: SPACE),
            "textModelId" to (enc?.textModelId ?: MODEL),
            "conceptSha256" to Teacher.conceptSha256(card),
            "looksLike" to pos.map { it.embedding.raw },
            "butNot" to butNot.map { it.embedding.raw },
            "ignore" to ignore.map { it.embedding.raw },
            "exampleCount" to 0,
            "exceptions" to emptyList<Any>(),
            "calibrationOffset" to 0.0,
            "userOffset" to 0.0,
            "thresholds" to th,
            "margin" to AUTO_MARGIN,
            "auto" to rawAuto
        )
        val cc = CompiledConcept(
            cid,
            pos.map { it.embedding },
            butNot.map { it.embedding },
            ignore.map { it.embedding },
            0.0,
            0.0,
            th,
            AUTO_MARGIN,
            raw = raw,
            auto = AutoRule(pos, comps, AUTO_MARGIN, chips)
        )
        return cc to chips
    }
}
