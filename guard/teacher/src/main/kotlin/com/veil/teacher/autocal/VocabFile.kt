package com.veil.teacher.autocal

import com.veil.teacher.Teacher
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

class VocabEntry(val name: String, val kind: String, val forms: List<String>, val excl: Set<Int>, val rel: Set<Int>)

/** Reads vocab.bin ("VVOC" v1) plus vocab.json. */
class VocabFile(bytes: ByteArray, json: String) {
    val n: Int
    val dim: Int
    val rows: List<DoubleArray>
    val thr: Array<DoubleArray>
    val meta: JsonObject = Json.parseToJsonElement(json).jsonObject
    val entries: List<VocabEntry>

    init {
        val b = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
        require(b.int == MAGIC) { "not a VVOC file" }
        require(b.int == 1) { "vocab version" }
        n = b.int
        dim = b.int
        val scale = FloatArray(n) { b.float }
        rows = List(n) { r ->
            AutoCal.l2(DoubleArray(dim) { b.get().toDouble() * scale[r].toDouble() })
        }
        thr = Array(n) { DoubleArray(3) { b.float.toDouble() } }
        entries = meta["entries"]!!.jsonArray.map { e ->
            val o = e.jsonObject
            fun ints(k: String) = o[k]!!.jsonArray.map { it.jsonPrimitive.int }.toSet()
            VocabEntry(
                o["name"]!!.jsonPrimitive.content,
                o["kind"]!!.jsonPrimitive.content,
                o["forms"]!!.jsonArray.map { it.jsonPrimitive.content },
                ints("excl"),
                ints("rel")
            )
        }
        require(entries.size == n) { "vocab.json has ${entries.size} entries, vocab.bin $n" }
    }

    fun lookup(word: String): Int? {
        val w = AutoCal.collapse(word)
        val s = Teacher.singular(w)
        return entries.indexOfFirst { it.kind == "noun" && (w in it.forms || s in it.forms) }.takeIf { it >= 0 }
    }

    companion object {
        private const val MAGIC = 0x434F5656 // "VVOC" little-endian

        fun load(bin: File, json: File) = VocabFile(bin.readBytes(), json.readText())
    }
}
