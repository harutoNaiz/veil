package com.veil.brain.judge

import com.veil.brain.contract.AutoRule
import com.veil.brain.contract.CompiledConcept
import com.veil.brain.contract.Embedding
import com.veil.brain.contract.Verdict
import java.util.Base64

object F16 {
    fun half(bits: Int): Float {
        val s = (bits shr 15) and 1
        val e = (bits shr 10) and 0x1F
        val m = bits and 0x3FF
        val v = when (e) {
            0 -> m * Math.pow(2.0, -24.0)
            31 -> if (m == 0) Double.POSITIVE_INFINITY else Double.NaN
            else -> (1.0 + m / 1024.0) * Math.pow(2.0, (e - 15).toDouble())
        }
        return (if (s == 1) -v else v).toFloat()
    }

    fun decode(b64: String, dim: Int): FloatArray {
        val raw = Base64.getDecoder().decode(b64)
        require(raw.size == 2 * dim) { "vectorF16 holds ${raw.size} bytes, expected ${2 * dim}" }
        return FloatArray(dim) {
            half((raw[2 * it].toInt() and 0xFF) or ((raw[2 * it + 1].toInt() and 0xFF) shl 8))
        }
    }
}

object Judge {
    const val T = 100.0
    const val NEAR_MISS_BAND = 0.1
    private val MODES = setOf("light", "balanced", "strict")

    private val decodes = java.util.concurrent.atomic.AtomicLong()

    /** How many f16 decodes have run since start; tests use it to prove decoding is not repeated per call. */
    val decodeCount: Long get() = decodes.get()

    /** The one place base64 f16 becomes a unit vector; reached through [Embedding.unit], which caches it. */
    fun decodeUnit(e: Embedding): DoubleArray {
        decodes.incrementAndGet()
        val v = F16.decode(e.vectorF16, e.dim).map { it.toDouble() }.toDoubleArray()
        val n = Math.max(Math.sqrt(v.sumOf { it * it }), 1e-12)
        return DoubleArray(v.size) { v[it] / n }
    }

    private fun matrix(es: List<Embedding>): List<DoubleArray> = es.map { it.unit }

    private fun dot(a: DoubleArray, b: DoubleArray): Double {
        var s = 0.0
        for (i in a.indices) s += a[i] * b[i]
        return s
    }

    private fun best(v: DoubleArray, m: List<DoubleArray>): Double = if (m.isEmpty()) -1.0 else m.maxOf { dot(v, it) }

    const val AUTO_NEAR_BAND = 0.02

    /** Auto path: per-word null-quantile thresholds; calibrationOffset and userOffset are ignored here. */
    private fun judgeAuto(vecs: List<DoubleArray>, cc: CompiledConcept, a: AutoRule, mode: String): List<Verdict> {
        val pos = a.positives.map { it.embedding.unit }
        val comp = a.competitors.map { it.embedding.unit }
        val centroid = cc.exampleCentroid?.unit
        val compThr = DoubleArray(comp.size) { a.competitors[it].thresholds.getValue("balanced") }
        return vecs.map { v ->
            val s = pos.map { dot(v, it) }
            val c = comp.indices.maxOfOrNull { dot(v, comp[it]) - compThr[it] } ?: -1e9
            var hide = false
            var bi = 0
            var bd = Double.NEGATIVE_INFINITY
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
            val se = centroid?.let { dot(v, it) }
            if (se != null && cc.exampleThreshold != null && se >= cc.exampleThreshold) hide = true
            val p = 1.0 / (1.0 + Math.exp(-T * bd))
            val decision = if (hide) {
                "hide"
            } else if (bd >= -AUTO_NEAR_BAND) {
                "nearMiss"
            } else {
                "leave"
            }
            Verdict(p, p, s[bi], mm - c, decision, se)
        }
    }

    fun judge(vecs: List<DoubleArray>, cc: CompiledConcept, mode: String): List<Verdict> {
        require(mode in MODES) { "mode must be one of $MODES, got $mode" }
        cc.auto?.let { return judgeAuto(vecs, cc, it, mode) }
        val ml = matrix(cc.looksLike)
        val mn = matrix(cc.butNot)
        val mi = matrix(cc.ignore)
        val thr = cc.thresholds.getValue(mode)
        val centroid = cc.exampleCentroid?.unit
        return vecs.map { v ->
            val sl = best(v, ml)
            val sn = best(v, mn)
            val si = best(v, mi)
            val l = doubleArrayOf(T * sl, T * sn, T * si)
            val mx = l.max()
            val ex = DoubleArray(3) { Math.exp(l[it] - mx) }
            val pRaw = ex[0] / ex.sum()
            val prob = (pRaw + (cc.calibrationOffset + cc.userOffset)).coerceIn(0.0, 1.0)
            val margin = sl - sn
            val se = centroid?.let { dot(v, it) }
            var hide = prob >= thr && margin >= cc.margin
            if (se != null && cc.exampleThreshold != null && se >= cc.exampleThreshold) hide = true
            val decision = if (hide) {
                "hide"
            } else if (prob >= thr - NEAR_MISS_BAND) {
                "nearMiss"
            } else {
                "leave"
            }
            Verdict(pRaw, prob, sl, margin, decision, se)
        }
    }
}
