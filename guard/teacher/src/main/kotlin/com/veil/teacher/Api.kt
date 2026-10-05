package com.veil.teacher

import com.veil.brain.contract.CompiledConcept
import java.util.concurrent.CopyOnWriteArrayList
import java.util.concurrent.atomic.AtomicReference

interface TextEncoder {
    val spaceId: String
    val textModelId: String
    fun encode(phrases: List<String>): List<FloatArray>
}

interface KeyProvider {
    fun key(): ByteArray
}

fun interface TextTokenizer {
    /** Lower-cased text to exactly 64 token ids (padded and truncated like the Workshop). */
    fun ids(text: String): LongArray
}

/** Atomic swap of the active concepts; listeners are told after every change (no restart). */
class ConceptRegistry {
    private val ref = AtomicReference<Map<String, CompiledConcept>>(emptyMap())
    private val listeners = CopyOnWriteArrayList<(Map<String, CompiledConcept>) -> Unit>()

    fun snapshot(): Map<String, CompiledConcept> = ref.get()

    operator fun get(id: String): CompiledConcept? = ref.get()[id]

    fun addListener(l: (Map<String, CompiledConcept>) -> Unit) {
        listeners.add(l)
    }

    fun swap(next: Map<String, CompiledConcept>) {
        val frozen = LinkedHashMap(next)
        ref.set(frozen)
        listeners.forEach { it(frozen) }
    }

    fun put(cc: CompiledConcept) = swap(ref.get() + (cc.conceptId to cc))

    fun remove(id: String) = swap(ref.get() - id)
}
