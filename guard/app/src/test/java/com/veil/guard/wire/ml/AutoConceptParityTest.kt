package com.veil.guard.wire.ml

import com.veil.brain.contract.Rect
import com.veil.brain.judge.Guards
import com.veil.brain.judge.Judge
import java.io.File
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.boolean
import kotlinx.serialization.json.double
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Test

/** A real compiled auto concept (phone-kit cats) parses in ConceptPack and judges like the Python twin. */
class AutoConceptParityTest {
    private val fx = listOf("../../workshop/twin/tests/fixtures/phone", "workshop/twin/tests/fixtures/phone")
        .map { File(it) }.first { File(it, "expected.json").isFile }
    private val exp = Json.parseToJsonElement(File(fx, "expected.json").readText()).jsonObject
    private val cc = ConceptPack.parse(File(fx, "concept.json").readText())[0]

    @Test
    fun parsesAutoAt768() {
        val a = cc.auto
        assertNotNull(a)
        assertEquals(null, ConceptPack.dimProblem(cc))
        assertEquals(1, a!!.positives.size)
        assertEquals(131, a.competitors.size)
    }

    @Test
    fun judgeMatchesTwin() {
        val vecs = exp["vectors"]!!.jsonArray.map { r -> r.jsonArray.map { it.jsonPrimitive.double }.toDoubleArray() }
        for (mode in listOf("light", "balanced", "strict")) {
            val want = exp["verdicts"]!!.jsonObject[mode]!!.jsonArray
            val got = Judge.judge(vecs, cc, mode)
            for (i in vecs.indices) {
                val w = want[i].jsonObject
                assertEquals("$mode#$i decision", w["decision"]!!.jsonPrimitive.content, got[i].decision)
                assertEquals("$mode#$i score", w["score"]!!.jsonPrimitive.double, got[i].score, 1e-4)
                assertEquals("$mode#$i margin", w["margin"]!!.jsonPrimitive.double, got[i].margin, 1e-4)
                assertEquals("$mode#$i p", w["probability"]!!.jsonPrimitive.double, got[i].probability, 1e-4)
            }
        }
    }

    private fun bools(o: JsonObject, k: String) = o[k]!!.jsonArray.map { it.jsonPrimitive.boolean }

    @Test
    fun guardsMatchTwin() {
        for (c in exp["guardCases"]!!.jsonArray.map { it.jsonObject }) {
            val pieces = c["pieces"]!!.jsonArray.map {
                val r = it.jsonObject["rect"]!!.jsonObject
                Guards.Piece(
                    it.jsonObject["source"]!!.jsonPrimitive.content,
                    Rect(
                        r["x"]!!.jsonPrimitive.int,
                        r["y"]!!.jsonPrimitive.int,
                        r["w"]!!.jsonPrimitive.int,
                        r["h"]!!.jsonPrimitive.int
                    )
                )
            }
            val hide = bools(c, "hide")
            val flat = bools(c, "flat")
            assertEquals(bools(c, "none"), Guards.apply(pieces, hide, null, null))
            assertEquals(bools(c, "flatOnly"), Guards.apply(pieces, hide, flat, null))
            assertEquals(bools(c, "agree"), Guards.apply(pieces, hide, flat, Guards.AGREE))
            assertEquals(bools(c, "wins"), Guards.apply(pieces, hide, flat, Guards.WINS))
        }
    }
}
