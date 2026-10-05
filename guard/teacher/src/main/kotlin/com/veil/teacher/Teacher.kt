package com.veil.teacher

import com.veil.brain.contract.CompiledConcept
import com.veil.brain.contract.Embedding
import com.veil.brain.contract.Record
import java.security.MessageDigest
import java.util.Base64
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

/** Port of workshop/twin/teacher.py. */
object Teacher {
    val LOOKS_LIKE =
        listOf("a photo of a {c}", "a cartoon {c}", "a drawing of a {c}", "a {c} emoji", "a close-up of a {c}")
    val IGNORE = listOf("a screenshot of an app", "text on a screen", "a user interface")
    val LOOKALIKES = mapOf(
        "cat" to listOf("a dog", "a fox", "a lion", "a stuffed toy"),
        "spider" to listOf("an ant", "a crab", "a scorpion", "a beetle")
    )
    private val DEFAULT_MODES = mapOf("light" to 0.7, "balanced" to 0.5, "strict" to 0.3)

    fun resource(name: String): JsonObject =
        Json.parseToJsonElement(Teacher::class.java.getResource("/$name")!!.readText()) as JsonObject

    fun singular(word: String): String =
        if (word.length > 2 && word.endsWith("s") && !word.endsWith("ss")) word.dropLast(1) else word

    fun conceptCard(word: String): Record {
        val text = word.trim().split(Regex("\\s+")).filter { it.isNotEmpty() }.joinToString(" ")
        val slug = text.lowercase().replace(Regex("[^a-z0-9._-]+"), "-").trim('-', '.').take(64)
        require(slug.isNotEmpty()) { "cannot make a concept from '$word'" }
        val sing = singular(text.lowercase())
        return linkedMapOf(
            "contractVersion" to "1.0",
            "conceptId" to slug,
            "displayName" to text.take(1).uppercase() + text.drop(1),
            "layer" to 2,
            "enabled" to true,
            "looksLike" to LOOKS_LIKE.map { it.replace("{c}", sing) },
            "butNot" to (LOOKALIKES[sing] ?: emptyList()),
            "scope" to "object",
            "coverStyle" to "solid",
            "showLabel" to false
        )
    }

    @Suppress("UNCHECKED_CAST")
    fun compile(
        concept: Record,
        enc: TextEncoder,
        calibration: JsonObject? = resource("calibration.json"),
        thresholds: JsonObject? = resource("thresholds.json")
    ): CompiledConcept {
        val cid = concept["conceptId"] as String
        val calib = calibration?.get("concepts")?.jsonObject?.get(cid) as? JsonObject
        val modes = DEFAULT_MODES +
            (
                thresholds?.get("modes")?.jsonObject?.mapValues {
                    it.value.jsonPrimitive.content.toDouble()
                } ?: emptyMap()
                )
        val conceptButNot = (concept["butNot"] as? List<String>) ?: emptyList()
        val extra = calib?.get("butNotExtra")?.jsonArray?.map { it.jsonPrimitive.content }
            ?.filter { it !in conceptButNot } ?: emptyList()
        val butNot = conceptButNot + extra
        val ignore = (concept["ignore"] as? List<String>)?.takeIf { it.isNotEmpty() } ?: IGNORE
        val looks = concept["looksLike"] as List<String>
        val phrases = looks + butNot + ignore
        val vecs = enc.encode(phrases)
        val embs = phrases.indices.map { i ->
            val f16 = encodeF16(vecs[i])
            val raw = linkedMapOf<String, Any?>(
                "contractVersion" to "1.0",
                "spaceId" to enc.spaceId,
                "modelId" to enc.textModelId,
                "dim" to vecs[i].size,
                "vectorF16" to f16,
                "kind" to "text",
                "text" to phrases[i].take(500)
            )
            Embedding(vecs[i].size, f16, raw)
        }
        val look = embs.subList(0, looks.size)
        val bn = embs.subList(looks.size, looks.size + butNot.size)
        val ig = embs.subList(looks.size + butNot.size, embs.size)
        val off = ((calib?.get("calibrationOffset") as? JsonPrimitive)?.doubleOrNull ?: 0.0).coerceIn(-1.0, 1.0)
        val thr = linkedMapOf(
            "light" to modes.getValue("light"),
            "balanced" to modes.getValue("balanced"),
            "strict" to modes.getValue("strict")
        )
        val margin = thresholds?.get("margin")?.jsonPrimitive?.doubleOrNull ?: 0.01
        val raw = linkedMapOf<String, Any?>(
            "contractVersion" to "1.0", "conceptId" to cid, "spaceId" to enc.spaceId, "textModelId" to enc.textModelId,
            "conceptSha256" to conceptSha256(concept),
            "looksLike" to look.map { it.raw }, "butNot" to bn.map { it.raw }, "ignore" to ig.map { it.raw },
            "exampleCount" to 0, "exceptions" to emptyList<Any>(), "calibrationOffset" to off, "userOffset" to 0.0,
            "thresholds" to thr, "margin" to margin
        )
        return CompiledConcept(cid, look, bn, ig, off, 0.0, thr, margin, raw = raw)
    }

    fun conceptSha256(concept: Any?): String {
        val sb = StringBuilder()
        canon(concept, sb)
        return MessageDigest.getInstance("SHA-256").digest(sb.toString().toByteArray(Charsets.UTF_8))
            .joinToString("") { "%02x".format(it) }
    }

    private fun canon(v: Any?, sb: StringBuilder) {
        when (v) {
            null -> sb.append("null")

            is Boolean, is Int, is Long, is Double -> sb.append(v)

            is String -> str(v, sb)

            is Map<*, *> -> {
                sb.append('{')
                v.entries.sortedBy { it.key as String }.forEachIndexed { i, e ->
                    if (i > 0) sb.append(',')
                    str(e.key as String, sb)
                    sb.append(':')
                    canon(e.value, sb)
                }
                sb.append('}')
            }

            is List<*> -> {
                sb.append('[')
                v.forEachIndexed { i, e ->
                    if (i > 0) sb.append(',')
                    canon(e, sb)
                }
                sb.append(']')
            }

            else -> error("unsupported ${v::class}")
        }
    }

    private fun str(s: String, sb: StringBuilder) {
        sb.append('"')
        for (ch in s) {
            when {
                ch == '"' -> sb.append("\\\"")
                ch == '\\' -> sb.append("\\\\")
                ch == '\n' -> sb.append("\\n")
                ch == '\r' -> sb.append("\\r")
                ch == '\t' -> sb.append("\\t")
                ch == '\b' -> sb.append("\\b")
                ch.code == 0x0c -> sb.append("\\f")
                ch < ' ' -> sb.append("\\u%04x".format(ch.code))
                else -> sb.append(ch)
            }
        }
        sb.append('"')
    }

    /** L2-normalise in double, little-endian float16, base64 (rules.encode_f16). */
    fun encodeF16(v: FloatArray): String {
        var n = 0.0
        for (x in v) n += x.toDouble() * x
        n = Math.sqrt(n)
        require(n.isFinite() && n != 0.0) { "cannot normalise a zero or non-finite vector" }
        val out = ByteArray(v.size * 2)
        for (i in v.indices) {
            val h = doubleToHalf(v[i].toDouble() / n)
            out[2 * i] = (h and 0xff).toByte()
            out[2 * i + 1] = (h shr 8).toByte()
        }
        return Base64.getEncoder().encodeToString(out)
    }

    /** Round-to-nearest-even double to IEEE half bits (finite inputs of magnitude <= 1). */
    fun doubleToHalf(d: Double): Int {
        val sign = if (d < 0 || (d == 0.0 && 1.0 / d < 0)) 0x8000 else 0
        val a = Math.abs(d)
        if (a == 0.0) return sign
        if (a >= 65520.0) return sign or 0x7c00
        val e = Math.getExponent(a)
        if (e < -14) return sign or Math.rint(a * (1 shl 24).toDouble()).toInt()
        var m = Math.rint((a / Math.pow(2.0, e.toDouble()) - 1.0) * 1024.0).toInt()
        var ee = e
        if (m == 1024) {
            m = 0
            ee++
        }
        return sign or ((ee + 15) shl 10) or m
    }
}
