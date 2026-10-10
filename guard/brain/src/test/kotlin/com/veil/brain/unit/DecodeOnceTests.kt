package com.veil.brain.unit

import com.veil.brain.contract.AutoRule
import com.veil.brain.contract.AutoTerm
import com.veil.brain.contract.CompiledConcept
import com.veil.brain.contract.Embedding
import com.veil.brain.judge.F16
import com.veil.brain.judge.Judge
import java.util.Base64
import java.util.Random
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertSame
import org.junit.Assert.assertTrue
import org.junit.Test

class DecodeOnceTests {
    private val dim = 768
    private val rnd = Random(7)

    private fun emb(): Embedding {
        val b = ByteArray(2 * dim)
        for (i in 0 until dim) {
            val bits = (rnd.nextInt(2) shl 15) or ((8 + rnd.nextInt(8)) shl 10) or rnd.nextInt(1024)
            b[2 * i] = bits.toByte()
            b[2 * i + 1] = (bits shr 8).toByte()
        }
        return Embedding(dim, Base64.getEncoder().encodeToString(b))
    }

    private fun term(name: String) = AutoTerm(
        name,
        emb(),
        linkedMapOf("light" to 0.02, "balanced" to 0.01, "strict" to 0.0)
    )

    private fun concept(nComp: Int = 131) = CompiledConcept(
        "c1", emptyList(), emptyList(), emptyList(), 0.0, 0.0,
        mapOf("light" to 0.3, "balanced" to 0.5, "strict" to 0.7), 0.04,
        exampleCentroid = emb(), exampleThreshold = 0.0,
        auto = AutoRule(
            listOf(term("p0"), term("p1")),
            List(nComp) { term("k$it") },
            0.04,
            emptyList()
        )
    )

    private fun unit(e: Embedding): DoubleArray {
        val v = F16.decode(e.vectorF16, e.dim).map { it.toDouble() }.toDoubleArray()
        val n = Math.max(Math.sqrt(v.sumOf { it * it }), 1e-12)
        return DoubleArray(v.size) { v[it] / n }
    }

    private fun dot(a: DoubleArray, b: DoubleArray) = a.indices.sumOf { a[it] * b[it] }

    /** The pre-cache implementation: decode everything on every call. */
    private fun reference(
        vecs: List<DoubleArray>,
        cc: CompiledConcept,
        mode: String
    ): List<Triple<String, Double, Double>> {
        val a = cc.auto!!
        val pos = a.positives.map { unit(it.embedding) }
        val comp = a.competitors.map { unit(it.embedding) }
        val centroid = cc.exampleCentroid?.let { unit(it) }
        return vecs.map { v ->
            val s = pos.map { dot(v, it) }
            val c = comp.indices.maxOf { dot(v, comp[it]) - a.competitors[it].thresholds.getValue("balanced") }
            var hide = false
            var bd = Double.NEGATIVE_INFINITY
            var bi = 0
            var mm = Double.NEGATIVE_INFINITY
            for (i in s.indices) {
                val th = a.positives[i].thresholds
                val d = s[i] - th.getValue(mode)
                val m = s[i] - th.getValue("balanced")
                if (s[i] >= th.getValue(mode) && m - c >= a.margin) hide = true
                if (d > bd) {
                    bd = d
                    bi = i
                }
                if (m > mm) mm = m
            }
            if (centroid != null && dot(v, centroid) >= cc.exampleThreshold!!) hide = true
            val decision = if (hide) {
                "hide"
            } else if (bd >= -Judge.AUTO_NEAR_BAND) {
                "nearMiss"
            } else {
                "leave"
            }
            Triple(decision, s[bi], mm - c)
        }
    }

    private fun queries(cc: CompiledConcept): List<DoubleArray> {
        val a = cc.auto!!
        val own = a.positives.map { it.embedding.unit } + a.competitors.take(5).map { it.embedding.unit }
        return own + List(10) { unit(emb()) }
    }

    @Test
    fun verdictsIdenticalToUncachedReference() {
        val cc = concept()
        val vecs = queries(cc)
        for (mode in listOf("light", "balanced", "strict")) {
            val ref = reference(vecs, cc, mode)
            val got = Judge.judge(vecs, cc, mode)
            assertEquals(ref.size, got.size)
            for (i in got.indices) {
                assertEquals(ref[i].first, got[i].decision)
                assertEquals(ref[i].second, got[i].score, 0.0)
                assertEquals(ref[i].third, got[i].margin, 0.0)
            }
        }
    }

    @Test
    fun decodesOncePerEmbeddingNotPerCall() {
        val cc = concept()
        val before = Judge.decodeCount
        val vecs = queries(cc)
        repeat(30) { Judge.judge(vecs, cc, "balanced") }
        val first = Judge.decodeCount - before
        // 2 positives + 131 competitors + 1 centroid, each decoded exactly once, however many calls
        assertEquals(134L, first)
        val again = Judge.decodeCount
        repeat(30) { Judge.judge(vecs, cc, "strict") }
        assertEquals(again, Judge.decodeCount)
        println("DECODE_ONCE decodes=$first for 30 judge calls (uncached would be ${30 * 134})")
    }

    @Test
    fun cachedVectorIsStableAndMatchesDirectDecode() {
        val e = emb()
        assertSame(e.unit, e.unit)
        assertArrayEquals(unit(e), e.unit, 0.0)
        assertEquals(e, e.copy())
    }

    @Test
    fun concurrentFirstUseDecodesOnce() {
        val e = emb()
        val before = Judge.decodeCount
        val pool = java.util.concurrent.Executors.newFixedThreadPool(8)
        val got = (1..16).map { pool.submit<DoubleArray> { e.unit } }.map { it.get() }
        pool.shutdown()
        assertEquals(1L, Judge.decodeCount - before)
        assertTrue(got.all { it === got[0] })
    }

    @Test
    fun hotSwappedConceptDecodesItsOwnVectors() {
        val old = concept(4)
        Judge.judge(queries(old), old, "balanced")
        val fresh = concept(4)
        val before = Judge.decodeCount
        Judge.judge(queries(fresh), fresh, "balanced")
        assertEquals(2 + 4 + 1L, Judge.decodeCount - before)
    }
}
