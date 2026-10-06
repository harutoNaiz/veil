package com.veil.guard.wire.ml

import com.veil.conductor.text.GemmaBpe
import com.veil.teacher.OrtTextEncoder
import com.veil.teacher.TextEncoder
import com.veil.teacher.TextTokenizer
import java.io.File

/** SigLIP2 tokenizer: GemmaBpe ids, truncated to [len] (EOS kept last) and padded like the twin (max_length=64). */
class Siglip2Tokenizer(private val bpe: GemmaBpe, private val len: Int = 64) : TextTokenizer {
    override fun ids(text: String): LongArray {
        val raw = bpe.encode(text)
        val src = if (raw.size > len) raw.copyOf(len).also { it[len - 1] = raw.last() } else raw
        return LongArray(len) { if (it < src.size) src[it].toLong() else bpe.padId.toLong() }
    }
}

/** Opens the 1.1 GB text tower only on first encode (an out-of-vocabulary word); [close] releases it. */
class LazyTextEncoder(private val store: ModelStore) :
    TextEncoder,
    AutoCloseable {
    override val spaceId = "siglip2-base-p16-224"
    override val textModelId = "siglip2-base-text"
    private var inner: OrtTextEncoder? = null

    fun available() = store.has(MODEL) && store.has(TOK)

    @Synchronized
    override fun encode(phrases: List<String>): List<FloatArray> {
        val e = inner ?: OrtTextEncoder(
            File(store.dir, MODEL).path,
            Siglip2Tokenizer(GemmaBpe.load(File(store.dir, TOK)))
        ).also { inner = it }
        return e.encode(phrases)
    }

    @Synchronized
    override fun close() {
        inner?.close()
        inner = null
    }

    companion object {
        const val MODEL = "siglip2-text.onnx"
        const val TOK = "siglip2-tok.bin"
    }
}
