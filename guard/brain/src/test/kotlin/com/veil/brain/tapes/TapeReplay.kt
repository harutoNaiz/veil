package com.veil.brain.tapes

import com.veil.brain.contract.FrameMeta
import com.veil.brain.contract.Rect
import com.veil.brain.contract.UiEvent
import com.veil.brain.motion.BrainPipeline
import java.io.File
import java.security.MessageDigest
import java.util.Base64
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.long

object TapeReplay {
    private val kinds = setOf("change", "look", "tracks", "maskPlan")

    fun parse(s: String): JsonObject = kotlinx.serialization.json.Json.parseToJsonElement(s).jsonObject

    fun sha(f: File): String = MessageDigest.getInstance("SHA-256").digest(f.readBytes()).joinToString("") {
        "%02x".format(it)
    }

    /** Canonical form: integers -> Long, fractions -> Double, no seq. */
    fun canon(v: Any?): Any? = when (v) {
        null -> null
        is Map<*, *> -> v.entries.associate { it.key as String to canon(it.value) }
        is List<*> -> v.map { canon(it) }
        is Int -> v.toLong()
        is Float -> v.toDouble()
        else -> v
    }

    fun fromJson(e: JsonElement): Any? = when (e) {
        is JsonNull -> null

        is JsonObject -> e.entries.associate { it.key to fromJson(it.value) }

        is JsonArray -> e.map { fromJson(it) }

        is JsonPrimitive ->
            when {
                e.isString -> e.content
                e.booleanOrNull != null -> e.booleanOrNull
                '.' in e.content || 'e' in e.content || 'E' in e.content -> e.content.toDouble()
                else -> e.content.toLong()
            }
    }

    fun firstDiff(a: Any?, b: Any?, path: String): String? {
        if (a is Map<*, *> && b is Map<*, *>) {
            for (k in (a.keys + b.keys).map { it as String }.sorted()) {
                if (k !in a) return "$path.$k missing in got"
                if (k !in b) return "$path.$k unexpected in got"
                firstDiff(a[k], b[k], "$path.$k")?.let { return it }
            }
            return null
        }
        if (a is List<*> && b is List<*>) {
            if (a.size != b.size) return "$path size ${a.size} vs ${b.size}"
            for (i in a.indices) firstDiff(a[i], b[i], "$path[$i]")?.let { return it }
            return null
        }
        return if (a == b && a?.javaClass == b?.javaClass) null else "$path got=$a want=$b"
    }

    /** Replays one tape; returns null when exact, else a mismatch description. */
    fun check(dir: File, meta: JsonObject, paramsJson: String): String? {
        val name = meta["name"]!!.jsonPrimitive.content
        val tin = File(dir, meta["tapeIn"]!!.jsonPrimitive.content)
        val tout = File(dir, meta["tapeOut"]!!.jsonPrimitive.content)
        if (sha(tin) != meta["tapeInSha256"]!!.jsonPrimitive.content) return "$name: tape-in sha changed"
        if (sha(tout) != meta["tapeOutSha256"]!!.jsonPrimitive.content) return "$name: tape-out sha changed"
        val mode = meta["mode"]!!.jsonPrimitive.content
        val got = ArrayList<Any?>()
        var pipe: BrainPipeline? = null
        var header: JsonObject? = null
        for (line in tin.readLines()) {
            if (line.isBlank()) continue
            val r = parse(line)
            when (r["kind"]!!.jsonPrimitive.content) {
                "header" -> {
                    header = r
                    pipe = BrainPipeline(mode, paramsJson)
                }

                "event" -> {
                    val e = r["event"]!!.jsonObject
                    @Suppress("UNCHECKED_CAST")
                    pipe!!.onEvent(
                        UiEvent(
                            type = e["type"]!!.jsonPrimitive.content,
                            tMs = e["tMs"]!!.jsonPrimitive.long,
                            dx = e["dx"]?.jsonPrimitive?.int ?: 0,
                            dy = e["dy"]?.jsonPrimitive?.int ?: 0,
                            packageName = e["packageName"]?.takeIf { it !is JsonNull }?.jsonPrimitive?.content,
                            raw = fromJson(e) as Map<String, Any?>
                        )
                    )
                }

                "finding" -> {
                    @Suppress("UNCHECKED_CAST")
                    pipe!!.enqueue(fromJson(r["finding"]!!) as Map<String, Any?>)
                }

                "frame" -> {
                    val h = header!!
                    val own =
                        (r["ownOverlay"]?.jsonArray ?: JsonArray(emptyList())).map {
                            val o = it.jsonObject
                            Rect(
                                o["x"]!!.jsonPrimitive.int,
                                o["y"]!!.jsonPrimitive.int,
                                o["w"]!!.jsonPrimitive.int,
                                o["h"]!!.jsonPrimitive.int
                            )
                        }
                    val fm =
                        FrameMeta(
                            r["frameId"]!!.jsonPrimitive.int,
                            r["tMs"]!!.jsonPrimitive.long,
                            h["width"]!!.jsonPrimitive.int,
                            h["height"]!!.jsonPrimitive.int,
                            h["screenWidth"]!!.jsonPrimitive.int,
                            h["screenHeight"]!!.jsonPrimitive.int,
                            own
                        )
                    got.addAll(
                        pipe!!.step(Base64.getDecoder().decode(r["thumb"]!!.jsonPrimitive.content), fm).map {
                            canon(it)
                        }
                    )
                }
            }
        }
        val want =
            tout.readLines().filter { it.isNotBlank() }.map { parse(it) }
                .filter { it["kind"]!!.jsonPrimitive.content in kinds }
                .map { fromJson(JsonObject(it.filterKeys { k -> k != "seq" })) }
        for (i in 0 until maxOf(got.size, want.size)) {
            if (i >= got.size || i >= want.size) return "$name: record count got=${got.size} want=${want.size}"
            val d = firstDiff(got[i], want[i], "")
            if (d != null) {
                @Suppress("UNCHECKED_CAST")
                val g = got[i] as Map<String, Any?>
                return "$name: frameId=${g["frameId"]} kind=${g["kind"]} record#$i diff at $d"
            }
        }
        return null
    }

    fun metas(dir: File): List<JsonObject> =
        parse(File(dir, "tapes.json").readText())["tapes"]!!.jsonArray.map { it.jsonObject }
}
