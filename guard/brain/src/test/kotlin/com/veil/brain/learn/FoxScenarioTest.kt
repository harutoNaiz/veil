package com.veil.brain.learn

import com.veil.brain.contract.CompiledConcept
import com.veil.brain.contract.Embedding
import com.veil.brain.gate.MiniJson
import com.veil.brain.judge.Judge
import org.junit.Assert.assertEquals
import org.junit.Assume.assumeNotNull
import org.junit.Test

@Suppress("UNCHECKED_CAST")
class FoxScenarioTest {
    private fun emb(m: Map<String, Any?>) = Embedding((m["dim"] as Number).toInt(), m["vectorF16"] as String)

    private fun embs(x: Any?) = (x as List<Map<String, Any?>>).map(::emb)

    private fun concept(m: Map<String, Any?>) = CompiledConcept(
        conceptId = m["conceptId"] as String,
        looksLike = embs(m["looksLike"]),
        butNot = embs(m["butNot"]),
        ignore = embs(m["ignore"]),
        calibrationOffset = (m["calibrationOffset"] as Number).toDouble(),
        userOffset = (m["userOffset"] as Number).toDouble(),
        thresholds = (m["thresholds"] as Map<String, Number>).mapValues { it.value.toDouble() },
        margin = (m["margin"] as Number).toDouble(),
        exampleCentroid = (m["exampleCentroid"] as Map<String, Any?>?)?.let(::emb),
        exampleThreshold = (m["exampleThreshold"] as Number?)?.toDouble()
    )

    private fun vecs(x: Any?) = (x as List<Map<String, Any?>>).map { CorrectionBook.decode(it["vec"] as String) }

    private fun decide(v: List<DoubleArray>, cc: CompiledConcept, mode: String, book: CorrectionBook?): List<String> =
        Judge.judge(v, cc, mode).mapIndexed { i, r ->
            (book?.filter(cc.conceptId, v[i], r) ?: r).decision
        }

    @Test
    fun replaysFoxDecisions() {
        val text = javaClass.classLoader.getResource("corrections/fox.json")?.readText()
        assumeNotNull(text) // fox.json is written by workshop/twin/fox_scenario.py
        val doc = MiniJson(text!!).parse() as Map<String, Any?>
        val cc = concept(doc["concept"] as Map<String, Any?>)
        val mode = doc["mode"] as String
        val fox = vecs(doc["fox"])
        val rep = vecs(doc["repost"])
        val cat = vecs(doc["cat"])
        val before = doc["before"] as Map<String, List<String>>
        val after = doc["after"] as Map<String, List<String>>
        assertEquals(before["fox"], decide(fox, cc, mode, null))
        assertEquals(before["cat"], decide(cat, cc, mode, null))
        val fi = (doc["feedbackIndex"] as Number).toInt()
        val book = CorrectionBook()
        book.record(Feedback("notThis", "cat"), fox[fi])
        val adj = book.adjust(cc)
        assertEquals(after["fox"], decide(fox, adj, mode, book))
        assertEquals(after["repost"], decide(rep, adj, mode, book))
        assertEquals(after["cat"], decide(cat, adj, mode, book))
    }
}
