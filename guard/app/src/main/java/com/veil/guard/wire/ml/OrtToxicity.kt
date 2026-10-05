package com.veil.guard.wire.ml

import ai.onnxruntime.OnnxTensor
import com.veil.conductor.TextClassifier
import com.veil.conductor.text.GemmaBpe
import com.veil.conductor.text.ToxPrep
import com.veil.guard.wire.WireHub
import java.io.File
import java.nio.LongBuffer

object OrtToxicity {
    private var cachedStamp = -1L
    private var cachedPath = ""
    private var cached: GemmaBpe? = null

    @Synchronized
    private fun pack(f: File): GemmaBpe {
        val c = cached
        if (c != null && cachedStamp == f.lastModified() && cachedPath == f.absolutePath) return c
        return GemmaBpe.load(f).also {
            cached = it
            cachedStamp = f.lastModified()
            cachedPath = f.absolutePath
        }
    }

    fun open(store: ModelStore): TextClassifier? {
        if (!store.has("toxicity-seq128.onnx") || !store.has("toxicity-tok.bin")) return null
        val bpe = pack(File(store.dir, "toxicity-tok.bin"))
        val session = store.session("toxicity-seq128.onnx") ?: return null
        val env = store.env
        return TextClassifier { text ->
            try {
                val (x, m) = ToxPrep.inputs(bpe.encode(text), 128, bpe.padId)
                val shape = longArrayOf(1, 128)
                OnnxTensor.createTensor(env, LongBuffer.wrap(x), shape).use { ti ->
                    OnnxTensor.createTensor(env, LongBuffer.wrap(m), shape).use { tm ->
                        session.run(mapOf("input_ids" to ti, "attention_mask" to tm)).use { res ->
                            val logits = (res.get(0) as OnnxTensor).floatBuffer
                            val arr = FloatArray(logits.remaining()).also { logits.get(it) }
                            ToxPrep.score(arr)
                        }
                    }
                }
            } catch (e: Exception) {
                WireHub.log?.write(mapOf("kind" to "warn", "what" to "tox-error"))
                0.0
            }
        }
    }
}
