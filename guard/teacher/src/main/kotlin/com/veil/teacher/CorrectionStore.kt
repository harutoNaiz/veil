package com.veil.teacher

import com.veil.brain.learn.CorrectionBook
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive

/** Keeps the correction book under the "corrections" key of the AES-GCM SecureStore. Local only. */
class CorrectionStore(private val store: SecureStore) {
    fun load(): CorrectionBook {
        val node = store.read()["corrections"] as? JsonObject ?: return CorrectionBook()
        return CorrectionBook.fromJson(plain(node) as Map<String, Any?>)
    }

    fun save(book: CorrectionBook) {
        val doc = store.read()
        store.write(JsonObject(doc + ("corrections" to json(book.toJson()))))
    }

    private fun plain(e: JsonElement): Any? = when (e) {
        is JsonObject -> e.mapValues { plain(it.value) }
        is JsonArray -> e.map(::plain)
        is JsonNull -> null
        is JsonPrimitive -> if (e.isString) e.content else e.content.toDouble()
    }

    private fun json(v: Any?): JsonElement = when (v) {
        null -> JsonNull
        is Map<*, *> -> JsonObject(v.entries.associate { it.key as String to json(it.value) })
        is List<*> -> JsonArray(v.map(::json))
        is Number -> JsonPrimitive(v)
        else -> JsonPrimitive(v.toString())
    }
}
