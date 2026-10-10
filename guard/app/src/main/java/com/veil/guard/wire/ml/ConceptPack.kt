package com.veil.guard.wire.ml

import com.veil.brain.contract.AutoRule
import com.veil.brain.contract.AutoTerm
import com.veil.brain.contract.CompiledConcept
import com.veil.brain.contract.Embedding
import com.veil.conductor.Concepts
import com.veil.guard.wire.WireHub
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

    /** finder stays empty: YOLOE text encoder export is blocked (variant C), boxes are described by SigLIP2. */
    fun toConcepts(all: List<CompiledConcept>): Concepts =
        Concepts(all, emptyList(), all.map { it.conceptId to keywords(it) }.filter { it.second.isNotEmpty() }.toMap())

    /** SigLIP2 describer output size; a concept in any other dim cannot be scored against it. */
    const val DESCRIBER_DIM = 768

    /** Why [c] cannot be used with a [dim]-wide describer, or null when it is fine. */
    fun dimProblem(c: CompiledConcept, dim: Int = DESCRIBER_DIM): String? {
        val auto = c.auto?.let { a -> (a.positives + a.competitors).map { it.embedding } } ?: emptyList()
        val all = c.looksLike + c.butNot + c.ignore + listOfNotNull(c.exampleCentroid) + auto
        val bad = all.map { it.dim }.filter { it != dim }.distinct()
        return if (bad.isEmpty()) null else "embedding dim $bad does not match describer dim $dim"
    }

    private fun defaultWarn(what: String, why: String) {
        WireHub.log?.write(linkedMapOf("kind" to "warn", "what" to what, "why" to why))
    }

    fun load(dir: File, warn: (what: String, why: String) -> Unit = ::defaultWarn): Concepts {
        val all = ArrayList<CompiledConcept>()
        dir.listFiles { f -> f.extension == "json" }?.sortedBy { it.name }?.forEach { f ->
            runCatching { parse(f.readText()) }
                .onFailure { warn("concept-rejected", "${f.name}: unreadable: $it") }
                .getOrNull()
                ?.forEach { c ->
                    val p = dimProblem(c)
                    if (p == null) all += c else warn("concept-rejected", "${f.name} (${c.conceptId}): $p")
                }
        }
        return toConcepts(all)
    }
}
