package com.veil.guard.wire.ml

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import com.veil.brain.contract.Rect
import com.veil.conductor.Frame
import com.veil.conductor.NsfwBox
import com.veil.conductor.NsfwDetector
import com.veil.conductor.layer1.NudeDecode
import java.nio.FloatBuffer

class OrtNsfwDetector(
    override val id: String,
    private val env: OrtEnvironment,
    private val session: OrtSession,
    private val size: Int,
    /** Hot-swap: accelerated session once ready (null until then). */
    private val upgrade: (() -> OrtSession?)? = null
) : NsfwDetector {
    override fun detect(frame: Frame, area: Rect): List<NsfwBox> {
        val argb = frame.argb ?: return emptyList()
        val m = frame.meta
        val crop = ImagePrep.crop(argb, m.width, m.height, m.screenWidth, m.screenHeight, area)
        val (img, lb) = ImagePrep.letterbox(crop, size)
        val buf = FloatArray(3 * size * size)
        ImagePrep.chw(img, 0f, 1f, buf, 0)
        val session = upgrade?.invoke() ?: this.session
        OnnxTensor.createTensor(env, FloatBuffer.wrap(buf), longArrayOf(1, 3, size.toLong(), size.toLong())).use { t ->
            session.run(mapOf(session.inputNames.first() to t)).use { res ->
                val tensor = res.get(0) as OnnxTensor
                val shape = tensor.info.shape // [1, 4+c, n]
                val c = (shape[1] - 4).toInt()
                val n = shape[2].toInt()
                val raw = FloatArray(tensor.floatBuffer.remaining()).also { tensor.floatBuffer.get(it) }
                // boxes are in crop-frame px; map back to screen px
                val sx = m.screenWidth.toDouble() / m.width
                val sy = m.screenHeight.toDouble() / m.height
                val ox = (area.x * m.width.toDouble() / m.screenWidth).toInt().coerceIn(0, m.width - 1)
                val oy = (area.y * m.height.toDouble() / m.screenHeight).toInt().coerceIn(0, m.height - 1)
                return NudeDecode.decode(raw, n, c, 0.2f, 0.45f, lb).map {
                    val r = it.rect
                    NsfwBox(
                        it.cls,
                        it.score,
                        Rect(
                            ((ox + r.x) * sx).toInt(),
                            ((oy + r.y) * sy).toInt(),
                            (r.w * sx).toInt(),
                            (r.h * sy).toInt()
                        )
                    )
                }
            }
        }
    }
}
