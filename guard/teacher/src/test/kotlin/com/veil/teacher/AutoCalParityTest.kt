package com.veil.teacher

import com.veil.brain.judge.Judge
import com.veil.teacher.autocal.AutoCal
import com.veil.teacher.autocal.BankFile
import com.veil.teacher.autocal.VocabFile
import java.io.File
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.double
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Test

class AutoCalParityTest {
    private val repo = File(System.getProperty("veil.repo") ?: "../..")
    private val fx = File(repo, "workshop/twin/tests/fixtures/autocal")
    private val expected = Json.parseToJsonElement(File(fx, "expected.json").readText()).jsonObject
    private val bank = BankFile.load(File(fx, "bank.bin"))
    private val vocab = VocabFile.load(File(fx, "vocab.bin"), File(fx, "vocab.json"))

    private fun dv(a: kotlinx.serialization.json.JsonArray) = DoubleArray(a.size) { a[it].jsonPrimitive.double }

    private fun strs(a: kotlinx.serialization.json.JsonArray) = a.map { it.jsonPrimitive.content }

    private fun enc(v: DoubleArray) = object : TextEncoder {
        override val spaceId = "stub-space"
        override val textModelId = "stub-text"
        override fun encode(phrases: List<String>) = phrases.map { FloatArray(v.size) { i -> v[i].toFloat() } }
    }

    private fun compile(q: JsonObject) = AutoCal.compileAuto(
        q["word"]!!.jsonPrimitive.content,
        strs(q["alsoHide"]!!.jsonArray),
        enc(dv(q["vector"]!!.jsonArray)),
        bank,
        vocab
    )

    @Test
    fun queriesMatchPython() {
        for (qe in expected["queries"]!!.jsonArray) {
            val q = qe.jsonObject
            val (cc, chips) = compile(q)
            val word = q["word"]!!.jsonPrimitive.content
            assertEquals("chips $word", strs(q["chips"]!!.jsonArray), chips)
            val auto = cc.auto!!
            assertEquals("competitors $word", strs(q["competitors"]!!.jsonArray), auto.competitors.map { it.term })
            val a = q["auto"]!!.jsonObject
            assertEquals("excluded $word", q["excluded"]!!.jsonPrimitive.int, (cc.raw["auto"] as Map<*, *>)["excluded"])
            val thr = q["thresholds"]!!.jsonObject
            for (m in AutoCal.MODES) {
                assertEquals(
                    "thr $m $word",
                    thr[m]!!.jsonPrimitive.double,
                    auto.positives[0].thresholds.getValue(m),
                    1e-4
                )
            }
        }
    }

    @Test
    fun vocabThresholdsRecompute() {
        val vt = expected["vocabThr"]!!.jsonArray
        for (i in 0 until vocab.n) {
            val t = AutoCal.thresholds(AutoCal.direction(vocab.rows[i], vocab.center), bank, vocab.entries[i].excl)
            for (m in 0..2) assertEquals("vocab $i/$m", vt[i].jsonArray[m].jsonPrimitive.double, t[m], 1e-4)
        }
    }

    @Test
    fun judgeMatchesPython() {
        val queries = expected["queries"]!!.jsonArray
        for (je in expected["judge"]!!.jsonArray) {
            val j = je.jsonObject
            val q = queries[j["query"]!!.jsonPrimitive.int].jsonObject
            val cc = compile(q).first
            val v = Judge.judge(listOf(dv(j["vector"]!!.jsonArray)), cc, j["mode"]!!.jsonPrimitive.content)[0]
            val e = j["verdict"]!!.jsonObject
            assertEquals(e["decision"]!!.jsonPrimitive.content, v.decision)
            assertEquals(e["score"]!!.jsonPrimitive.double, v.score, 1e-6)
            assertEquals(e["margin"]!!.jsonPrimitive.double, v.margin, 1e-6)
            assertEquals(e["probability"]!!.jsonPrimitive.double, v.probability, 1e-6)
        }
    }

    @Test
    fun realBankLoadsAndScans() {
        val dir =
            listOf("v1", "mini", "smoke").map {
                File(repo, "data/bank/$it")
            }.firstOrNull { File(it, "bank.bin").isFile }
                ?: return
        val t0 = System.nanoTime()
        val b = BankFile.load(File(dir, "bank.bin"))
        val loadMs = (System.nanoTime() - t0) / 1_000_000
        val e = AutoCal.l2(DoubleArray(b.dim) { (it % 7) - 3.0 })
        val t1 = System.nanoTime()
        b.scores(e)
        println("BANKLOAD n=${b.n} loadMs=$loadMs scanMs=${(System.nanoTime() - t1) / 1_000_000}")
    }
}
