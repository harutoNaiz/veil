package com.veil.brain.learn

import com.veil.brain.contract.CompiledConcept
import com.veil.brain.contract.Verdict
import com.veil.brain.judge.F16
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.Base64

/** One piece of user feedback on a Layer 2 cover (the Feedback contract subset the book needs). */
data class Feedback(val kind: String, val conceptId: String, val layer: Int = 2)

/** Threshold nudge and bounded exception list per concept; Layer 1 is never touched. No network code here. */
class CorrectionBook {
    private val nudge = HashMap<String, Double>()
    private val exceptions = HashMap<String, ArrayList<DoubleArray>>()

    fun record(fb: Feedback, vec: DoubleArray?) {
        require(fb.layer == 2 && fb.conceptId !in LAYER1_IDS) { "Layer 1 cannot be corrected" }
        val cur = nudge[fb.conceptId] ?: 0.0
        when (fb.kind) {
            "notThis" -> {
                nudge[fb.conceptId] = minOf(cur + STEP, CAP)
                if (vec != null) {
                    val list = exceptions.getOrPut(fb.conceptId) { ArrayList() }
                    list.add(unit(roundTrip(vec)))
                    while (list.size > MAX_EXCEPTIONS) list.removeAt(0)
                }
            }

            "missed" -> nudge[fb.conceptId] = maxOf(cur - STEP, -CAP)
        }
    }

    fun adjust(cc: CompiledConcept, layer: Int = 2): CompiledConcept {
        if (protectedConcept(cc.conceptId, layer)) return cc
        return cc.copy(userOffset = -(nudge[cc.conceptId] ?: 0.0))
    }

    fun filter(conceptId: String, vec: DoubleArray, v: Verdict, layer: Int = 2): Verdict {
        if (protectedConcept(conceptId, layer)) return v
        val ex = exceptions[conceptId] ?: return v
        val u = unit(vec)
        val sim = ex.maxOfOrNull { e -> e.indices.sumOf { e[it] * u[it] } } ?: return v
        return if (sim >= EXCEPTION_SIM) v.copy(decision = "leave") else v
    }

    fun nudgeOf(conceptId: String): Double = nudge[conceptId] ?: 0.0

    fun exceptionCount(conceptId: String): Int = exceptions[conceptId]?.size ?: 0

    /** `{"concepts": {id: {"nudge": d, "exceptions": [b64 f16, ...]}}}` as plain maps and lists. */
    fun toJson(): Map<String, Any?> {
        val ids = (nudge.keys + exceptions.keys).sorted()
        val concepts = LinkedHashMap<String, Any?>()
        for (id in ids) {
            concepts[id] = linkedMapOf(
                "nudge" to (nudge[id] ?: 0.0),
                "exceptions" to (exceptions[id] ?: emptyList<DoubleArray>()).map { encode(it) }
            )
        }
        return linkedMapOf("concepts" to concepts)
    }

    companion object {
        const val MAX_EXCEPTIONS = 64
        const val STEP = 0.02
        const val CAP = 0.15
        const val EXCEPTION_SIM = 0.92
        val LAYER1_IDS = setOf("nsfw", "nudity")

        private fun protectedConcept(id: String, layer: Int) = layer == 1 || id in LAYER1_IDS

        private fun unit(v: DoubleArray): DoubleArray {
            val n = Math.max(Math.sqrt(v.sumOf { it * it }), 1e-12)
            return DoubleArray(v.size) { v[it] / n }
        }

        private fun roundTrip(v: DoubleArray): DoubleArray {
            val u = unit(v)
            return F16.decode(encode(u), u.size).map { it.toDouble() }.toDoubleArray()
        }

        /** Unit-normalise then store as little-endian float16, base64 (same as the contract). */
        fun encode(v: DoubleArray): String {
            val u = unit(v)
            val buf = ByteBuffer.allocate(2 * u.size).order(ByteOrder.LITTLE_ENDIAN)
            for (x in u) buf.putShort(toHalf(x.toFloat()))
            return Base64.getEncoder().encodeToString(buf.array())
        }

        private fun toHalf(f: Float): Short {
            val b = java.lang.Float.floatToRawIntBits(f)
            val sign = (b ushr 16) and 0x8000
            val e = ((b ushr 23) and 0xFF) - 127 + 15
            val m = b and 0x7FFFFF
            val h: Int
            if (e >= 31) {
                h = 0x7C00
            } else if (e <= 0) {
                if (e < -10) {
                    h = 0
                } else {
                    val full = m or 0x800000
                    val shift = 14 - e
                    var q = full shr shift
                    val rem = full and ((1 shl shift) - 1)
                    val half = 1 shl (shift - 1)
                    if (rem > half || (rem == half && (q and 1) == 1)) q++
                    h = q
                }
            } else {
                var q = (e shl 10) or (m shr 13)
                val rem = m and 0x1FFF
                if (rem > 0x1000 || (rem == 0x1000 && (q and 1) == 1)) q++
                h = q
            }
            return (sign or h).toShort()
        }

        fun decode(b64: String): DoubleArray {
            val dim = Base64.getDecoder().decode(b64).size / 2
            return F16.decode(b64, dim).map { it.toDouble() }.toDoubleArray()
        }

        @Suppress("UNCHECKED_CAST")
        fun fromJson(doc: Map<String, Any?>): CorrectionBook {
            val book = CorrectionBook()
            val concepts = (doc["concepts"] as? Map<String, Any?>) ?: return book
            for ((id, c) in concepts) {
                val m = c as Map<String, Any?>
                book.nudge[id] = (m["nudge"] as Number).toDouble()
                book.exceptions[id] = ArrayList((m["exceptions"] as List<String>).map { unit(decode(it)) })
            }
            return book
        }
    }
}
