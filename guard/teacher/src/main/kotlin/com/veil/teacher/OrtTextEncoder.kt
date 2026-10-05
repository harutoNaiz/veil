package com.veil.teacher

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import java.nio.LongBuffer

/** SigLIP2 text tower on onnxruntime (JVM or Android; the app supplies the runtime artifact). */
class OrtTextEncoder(modelPath: String, private val tokenizer: TextTokenizer) :
    TextEncoder,
    AutoCloseable {
    override val spaceId = "siglip2-base-p16-224"
    override val textModelId = "siglip2-base-text"
    private val env = OrtEnvironment.getEnvironment()
    private val session: OrtSession = env.createSession(modelPath, OrtSession.SessionOptions())

    override fun encode(phrases: List<String>): List<FloatArray> = phrases.map { p ->
        val ids = tokenizer.ids(p.lowercase())
        OnnxTensor.createTensor(env, LongBuffer.wrap(ids), longArrayOf(1, ids.size.toLong())).use { t ->
            session.run(mapOf("input_ids" to t)).use { r ->
                @Suppress("UNCHECKED_CAST")
                val row = (r[0].value as Array<FloatArray>)[0]
                var n = 0.0
                for (x in row) n += x.toDouble() * x
                val s = Math.sqrt(n).coerceAtLeast(1e-12).toFloat()
                FloatArray(row.size) { row[it] / s }
            }
        }
    }

    override fun close() = session.close()
}
