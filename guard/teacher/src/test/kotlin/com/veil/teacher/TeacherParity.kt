package com.veil.teacher

import ai.djl.huggingface.tokenizers.HuggingFaceTokenizer
import java.io.File
import java.util.Base64
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class TeacherParity {
    private fun toJson(v: Any?): JsonElement = when (v) {
        null -> kotlinx.serialization.json.JsonNull
        is Boolean -> JsonPrimitive(v)
        is Number -> JsonPrimitive(v)
        is String -> JsonPrimitive(v)
        is Map<*, *> -> JsonObject(v.entries.associate { it.key as String to toJson(it.value) })
        is List<*> -> JsonArray(v.map { toJson(it) })
        else -> error("bad")
    }

    private fun f16(b64: String): DoubleArray {
        val b = Base64.getDecoder().decode(b64)
        return DoubleArray(b.size / 2) {
            val h = (b[2 * it].toInt() and 0xff) or ((b[2 * it + 1].toInt() and 0xff) shl 8)
            val e = (h shr 10) and 0x1f
            val m = h and 0x3ff
            val mag = if (e == 0) m * Math.pow(2.0, -24.0) else (1 + m / 1024.0) * Math.pow(2.0, (e - 15).toDouble())
            if (h and 0x8000 != 0) -mag else mag
        }
    }

    @Test fun parity() {
        val repo = File(System.getProperty("veil.repo"))
        val onnx = File(repo, "data/forge/siglip2/siglip2-text.onnx")
        val tokFile = File(repo, "data/forge/siglip2/tokenizer.json")
        val ref = Json.parseToJsonElement(
            File(repo, "data/ch5/teacher-ref.json").readText()
        ).jsonObject["concepts"]!!.jsonArray
        val tok = HuggingFaceTokenizer.builder().optTokenizerPath(tokFile.toPath())
            .optPadding(true).optPadToMaxLength().optMaxLength(64).optTruncation(true).build()
        val ids = TextTokenizer { t -> tok.encode(t).ids.also { assertEquals(64, it.size) } }
        OrtTextEncoder(onnx.path, ids).use { enc ->
            for (c in ref) {
                val o = c.jsonObject
                val word = o["word"]!!.jsonPrimitive.content
                val t0 = System.nanoTime()
                val card = Teacher.conceptCard(word)
                val cc = Teacher.compile(card, enc)
                println("card ms=${(System.nanoTime() - t0) / 1_000_000} word=$word")
                assertEquals(o["card"], toJson(card))
                assertEquals(o["conceptSha256"]!!.jsonPrimitive.content, Teacher.conceptSha256(card))
                val mine = (cc.looksLike + cc.butNot + cc.ignore).map { f16(it.vectorF16) }
                val theirs = o["prompts"]!!.jsonArray
                assertEquals(theirs.size, mine.size)
                for (i in mine.indices) {
                    val b = f16(theirs[i].jsonObject["vectorF16"]!!.jsonPrimitive.content)
                    var dot = 0.0
                    var na = 0.0
                    var nb = 0.0
                    for (k in b.indices) {
                        dot += mine[i][k] * b[k]
                        na += mine[i][k] * mine[i][k]
                        nb += b[k] * b[k]
                    }
                    val cos = dot / Math.sqrt(na * nb)
                    assertTrue("$word prompt $i cos=$cos", cos >= 0.99)
                }
            }
        }
    }
}
