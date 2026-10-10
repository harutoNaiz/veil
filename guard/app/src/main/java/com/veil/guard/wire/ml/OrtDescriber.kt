package com.veil.guard.wire.ml

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import com.veil.conductor.Describer
import com.veil.conductor.Frame
import com.veil.conductor.Piece
import com.veil.guard.wire.ml.accel.BatchPlan
import java.nio.FloatBuffer
import java.util.concurrent.Callable
import java.util.concurrent.Executors
import kotlin.math.sqrt

/**
 * SigLIP2 image tower: crop, 224 stretch, (v-0.5)/0.5, L2-normalised fingerprints. Pieces are split over the
 * available batch sessions (1/4/16) with the fewest padded slots; preprocessing runs on a small thread pool.
 */
class OrtDescriber(
    private val env: OrtEnvironment,
    private val sessions: Map<Int, OrtSession>,
    /** Hot-swap: accelerated sessions once ready (null until then). */
    private val upgrade: (() -> Map<Int, OrtSession>?)? = null
) : Describer {
    override fun describe(frame: Frame, pieces: List<Piece>): List<FloatArray> {
        val argb = frame.argb ?: error("no pixels")
        val m = frame.meta
        val n = pieces.size
        val per = 3 * 224 * 224
        val sessions = upgrade?.invoke() ?: this.sessions
        val plan = BatchPlan.plan(n, sessions.keys)
        check(n == 0 || plan.isNotEmpty()) { "no image sessions" }
        val out = ArrayList<FloatArray>(n)
        var at = 0
        for (b in plan) {
            val take = minOf(b, n - at)
            val first = at
            val buf = FloatArray(b * per) // padded slots stay zero; rows are independent so real rows are unaffected
            val jobs = (0 until take).map { i ->
                Callable {
                    val crop = ImagePrep.crop(
                        argb,
                        m.width,
                        m.height,
                        m.screenWidth,
                        m.screenHeight,
                        pieces[first + i].rect
                    )
                    ImagePrep.chw(ImagePrep.resizeBilinear(crop, 224, 224), 0.5f, 0.5f, buf, i * per)
                }
            }
            if (take == 1) jobs[0].call() else pool.invokeAll(jobs).forEach { it.get() }
            OnnxTensor.createTensor(env, FloatBuffer.wrap(buf), longArrayOf(b.toLong(), 3, 224, 224)).use { t ->
                sessions.getValue(b).run(mapOf("pixel_values" to t)).use { res ->
                    val rows = res.get("fingerprint").get().value as Array<*>
                    for (i in 0 until take) out += normalise(rows[i] as FloatArray)
                }
            }
            at += take
        }
        return out
    }

    private companion object {
        val pool = Executors.newFixedThreadPool(4) { r -> Thread(r, "veil-prep").apply { isDaemon = true } }

        fun normalise(v: FloatArray): FloatArray {
            var s = 0.0
            for (x in v) s += x.toDouble() * x
            val norm = sqrt(s).toFloat().coerceAtLeast(1e-12f)
            return FloatArray(v.size) { v[it] / norm }
        }
    }
}
