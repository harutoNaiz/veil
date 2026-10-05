package com.veil.guard.wire.ml

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import com.veil.conductor.Describer
import com.veil.conductor.Frame
import com.veil.conductor.Piece
import java.nio.FloatBuffer
import kotlin.math.sqrt

/** SigLIP2 image tower: crop, 224 stretch, (v-0.5)/0.5, batch 1/4/16 padded, L2-normalised fingerprints. */
class OrtDescriber(private val env: OrtEnvironment, private val sessions: Map<Int, OrtSession>) : Describer {
    override fun describe(frame: Frame, pieces: List<Piece>): List<FloatArray> {
        val argb = frame.argb ?: error("no pixels")
        val m = frame.meta
        val n = pieces.size
        val b = listOf(1, 4, 16).first { it >= n && sessions.containsKey(it) }
        val per = 3 * 224 * 224
        val buf = FloatArray(b * per)
        for (i in 0 until b) {
            val p = pieces[minOf(i, n - 1)]
            val crop = ImagePrep.crop(argb, m.width, m.height, m.screenWidth, m.screenHeight, p.rect)
            ImagePrep.chw(ImagePrep.resizeBilinear(crop, 224, 224), 0.5f, 0.5f, buf, i * per)
        }
        OnnxTensor.createTensor(env, FloatBuffer.wrap(buf), longArrayOf(b.toLong(), 3, 224, 224)).use { t ->
            sessions.getValue(b).run(mapOf("pixel_values" to t)).use { res ->
                val rows = (res.get("fingerprint").get().value as Array<*>).map { it as FloatArray }
                return rows.take(n).map { v ->
                    val norm = sqrt(v.sumOf { (it * it).toDouble() }).toFloat().coerceAtLeast(1e-12f)
                    FloatArray(v.size) { v[it] / norm }
                }
            }
        }
    }
}
