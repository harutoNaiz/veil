package com.veil.brain.unit

import com.veil.brain.cache.FingerprintCache
import com.veil.brain.cache.Sig
import com.veil.brain.contract.CompiledConcept
import com.veil.brain.contract.Embedding
import com.veil.brain.judge.Judge
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.double
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.long
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

private fun res(name: String): JsonObject = Json.parseToJsonElement(
    GoldenTests::class.java.getResourceAsStream("/$name")!!.readBytes().decodeToString()
).jsonObject

private fun emb(e: JsonElement) =
    Embedding(e.jsonObject["dim"]!!.jsonPrimitive.int, e.jsonObject["vectorF16"]!!.jsonPrimitive.content)

private fun embs(o: JsonObject, k: String) = (o[k] as? JsonArray)?.map { emb(it) } ?: emptyList()

class GoldenTests {
    @Test
    fun judgeMatchesPython() {
        var n = 0
        for (c in res("judge-golden.json")["cases"]!!.jsonArray) {
            val o = c.jsonObject
            val cj = o["concept"]!!.jsonObject
            val mode = o["mode"]!!.jsonPrimitive.content
            val cc = CompiledConcept(
                conceptId = cj["conceptId"]!!.jsonPrimitive.content,
                looksLike = embs(cj, "looksLike"),
                butNot = embs(cj, "butNot"),
                ignore = embs(cj, "ignore"),
                calibrationOffset = cj["calibrationOffset"]?.jsonPrimitive?.double ?: 0.0,
                userOffset = cj["userOffset"]?.jsonPrimitive?.double ?: 0.0,
                thresholds = cj["thresholds"]!!.jsonObject.mapValues { it.value.jsonPrimitive.double },
                margin = cj["margin"]?.jsonPrimitive?.double ?: 0.0,
                exampleCentroid = cj["exampleCentroid"]?.takeIf { it !is JsonNull }?.let { emb(it) },
                exampleThreshold = cj["exampleThreshold"]?.takeIf { it !is JsonNull }?.jsonPrimitive?.double
            )
            val vecs = o["vecs"]!!.jsonArray.map { r -> r.jsonArray.map { it.jsonPrimitive.double }.toDoubleArray() }
            val exp = o["verdicts"]!!.jsonArray
            val got = Judge.judge(vecs, cc, mode)
            assertEquals(exp.size, got.size)
            val thr = cc.thresholds.getValue(mode)
            for (i in got.indices) {
                val e = exp[i].jsonObject
                val g = got[i]
                assertEquals(e["p_raw"]!!.jsonPrimitive.double, g.pRaw, 1e-9)
                assertEquals(e["probability"]!!.jsonPrimitive.double, g.probability, 1e-9)
                assertEquals(e["score"]!!.jsonPrimitive.double, g.score, 1e-9)
                assertEquals(e["margin"]!!.jsonPrimitive.double, g.margin, 1e-9)
                val d = e["decision"]!!.jsonPrimitive.content
                val nearEdge = Math.abs(g.probability - thr) < 0.001 || Math.abs(g.probability - (thr - 0.1)) < 0.001
                if (!nearEdge) assertEquals("case $n verdict $i", d, g.decision)
            }
            n++
        }
        assertTrue(n >= 6)
    }

    @Test
    fun cacheMatchesPython() {
        val g = res("cache-golden.json")
        val c = FingerprintCache(capacity = g["capacity"]!!.jsonPrimitive.int)
        for ((i, opEl) in g["ops"]!!.jsonArray.withIndex()) {
            val o = opEl.jsonObject
            val h = o["h"]!!.jsonPrimitive.content.toULong().toLong()
            val t = o["t"]!!.jsonPrimitive.long
            val sig = o["sig"]?.jsonObject?.let { s ->
                Sig(
                    s["thumb"]!!.jsonArray.map { it.jsonPrimitive.int.toByte() }.toByteArray(),
                    s["w"]!!.jsonPrimitive.int,
                    s["h"]!!.jsonPrimitive.int
                )
            }
            when (o["op"]!!.jsonPrimitive.content) {
                "put" -> c.put(h, floatArrayOf(o["fp"]!!.jsonPrimitive.double.toFloat()), t, sig)

                "clear" -> c.clear()

                else -> {
                    val got = c.get(h, t, sig)
                    val exp = o["expect"]
                    if (exp == null || exp is JsonNull) {
                        assertEquals("op $i", null, got)
                    } else {
                        assertEquals("op $i", exp.jsonPrimitive.double.toFloat(), got!![0])
                    }
                }
            }
        }
        assertEquals(g["hits"]!!.jsonPrimitive.int, c.hits)
        assertEquals(g["misses"]!!.jsonPrimitive.int, c.misses)
    }

    @Test
    fun brainIsPortable() {
        val text = java.io.File(System.getProperty("veil.repo"), "guard/brain/build.gradle.kts").readText().lowercase()
        assertTrue(!text.contains("android"))
    }
}
