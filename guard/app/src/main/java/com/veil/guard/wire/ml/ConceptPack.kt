package com.veil.guard.wire.ml

import com.veil.brain.contract.AutoRule
import com.veil.brain.contract.AutoTerm
import com.veil.brain.contract.CompiledConcept
import com.veil.brain.contract.Embedding
import com.veil.conductor.Concepts
import java.io.File
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

/** Pure: compiled-concept JSON (one concept or an object with a concepts array) to brain types. */
object ConceptPack {
    private fun emb(e: JsonElement) =
        Embedding(e.jsonObject["dim"]!!.jsonPrimitive.int, e.jsonObject["vectorF16"]!!.jsonPrimitive.content)

    private fun embs(o: JsonObject, k: String) = (o[k] as? JsonArray)?.map { emb(it) } ?: emptyList()

    private fun toAny(e: JsonElement): Any? = when (e) {
        is JsonNull -> null
        is JsonObject -> e.mapValues { toAny(it.value) }
        is JsonArray -> e.map { toAny(it) }
        else -> e.jsonPrimitive.content
    }

    private fun autoTerms(a: JsonObject, k: String) = (a[k] as? JsonArray)?.map {
        val o = it.jsonObject
        AutoTerm(
            o["term"]!!.jsonPrimitive.content,
            emb(o["embedding"]!!),
            o["thresholds"]!!.jsonObject.mapValues { t -> t.value.jsonPrimitive.double }
        )
    } ?: emptyList()

    private fun auto(cj: JsonObject): AutoRule? = (cj["auto"] as? JsonObject)?.let { a ->
        AutoRule(
            autoTerms(a, "positives"),
            autoTerms(a, "competitors"),
            a["margin"]?.jsonPrimitive?.double ?: 0.0,
            (a["chips"] as? JsonArray)?.map { c -> c.jsonPrimitive.content } ?: emptyList()
        )
    }

    private fun one(cj: JsonObject) = CompiledConcept(
        conceptId = cj["conceptId"]!!.jsonPrimitive.content,
        looksLike = embs(cj, "looksLike"),
        butNot = embs(cj, "butNot"),
        ignore = embs(cj, "ignore"),
        calibrationOffset = cj["calibrationOffset"]?.jsonPrimitive?.double ?: 0.0,
        userOffset = cj["userOffset"]?.jsonPrimitive?.double ?: 0.0,
        thresholds = cj["thresholds"]!!.jsonObject.mapValues { it.value.jsonPrimitive.double },
        margin = cj["margin"]?.jsonPrimitive?.double ?: 0.0,
        exampleCentroid = cj["exampleCentroid"]?.takeIf { it !is JsonNull }?.let { emb(it) },
        exampleThreshold = cj["exampleThreshold"]?.takeIf { it !is JsonNull }?.jsonPrimitive?.double,
        raw = cj.mapValues { toAny(it.value) },
        auto = auto(cj)
    )

    fun parse(json: String): List<CompiledConcept> {
        val root = Json.parseToJsonElement(json).jsonObject
        val arr = root["concepts"] as? JsonArray
        return if (arr != null) arr.map { one(it.jsonObject) } else listOf(one(root))
    }

    private fun keywords(c: CompiledConcept): List<String> =
        (c.raw["keywords"] as? List<*>)?.filterIsInstance<String>() ?: emptyList()

    fun toConcepts(all: List<CompiledConcept>): Concepts =
        Concepts(all, emptyList(), all.map { it.conceptId to keywords(it) }.filter { it.second.isNotEmpty() }.toMap())

    fun load(dir: File): Concepts {
        val all = ArrayList<CompiledConcept>()
        dir.listFiles { f -> f.extension == "json" }?.sortedBy { it.name }?.forEach { f ->
            runCatching { all += parse(f.readText()) }
        }
        return toConcepts(all)
    }
}
