package com.veil.guard.wire.ml

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import com.veil.brain.contract.Rect
import com.veil.conductor.Finder
import com.veil.conductor.Frame
import com.veil.conductor.regions.YoloeDecode
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.FloatBuffer

/**
 * YOLOE-26s finder (yoloe-26s-embed-top100.onnx): square 640 letterbox padded with 114, fixed proposal_pe.
 * Boxes come back in screen px, best objectness first (decode in YoloeDecode). The fingerprint is returned too,
 * but with no exported text encoder (variant C) the lane describes the boxes with SigLIP2 instead.
 */
class OrtFinder(private val env: OrtEnvironment, private val session: OrtSession, private val proposalPe: FloatArray) :
    Finder {
    override fun boxes(frame: Frame, area: Rect): List<Pair<Rect, FloatArray>> {
        val argb = frame.argb ?: return emptyList()
        val m = frame.meta
        val crop = ImagePrep.crop(argb, m.width, m.height, m.screenWidth, m.screenHeight, area)
        val lb = YoloeDecode.letterbox(crop.w, crop.h)
        val sz = YoloeDecode.SIZE
        val canvas = IntArray(sz * sz) { (0xFF shl 24) or (YoloeDecode.PAD * 0x010101) }
        val small = ImagePrep.resizeBilinear(crop, lb.newW, lb.newH)
        for (y in 0 until lb.newH) {
            val dy = y + lb.top
            if (dy !in 0 until sz) continue
            for (x in 0 until lb.newW) {
                val dx = x + lb.left
                if (dx in 0 until sz) canvas[dy * sz + dx] = small.px[y * lb.newW + x]
            }
        }
        val buf = FloatArray(3 * sz * sz)
        ImagePrep.chw(Img(canvas, sz, sz), 0f, 1f, buf, 0)
        OnnxTensor.createTensor(env, FloatBuffer.wrap(buf), longArrayOf(1, 3, sz.toLong(), sz.toLong())).use { img ->
            OnnxTensor.createTensor(env, FloatBuffer.wrap(proposalPe), longArrayOf(1, 8, 512)).use { pe ->
                session.run(mapOf("images" to img, "proposal_pe" to pe)).use { res ->
                    val bx = flat(res.get("boxes").get() as OnnxTensor)
                    val obj = flat(res.get("objectness").get() as OnnxTensor)
                    val fp = flat(res.get("fingerprint").get() as OnnxTensor)
                    val dim = fp.size / obj.size
                    val sx = m.screenWidth.toDouble() / m.width
                    val sy = m.screenHeight.toDouble() / m.height
                    val ox = (area.x * m.width.toDouble() / m.screenWidth).toInt().coerceIn(0, m.width - 1)
                    val oy = (area.y * m.height.toDouble() / m.screenHeight).toInt().coerceIn(0, m.height - 1)
                    return YoloeDecode.select(bx, obj, crop.w, crop.h).map { d ->
                        val x0 = ((ox + d.x1) * sx).toInt().coerceIn(0, m.screenWidth - 1)
                        val y0 = ((oy + d.y1) * sy).toInt().coerceIn(0, m.screenHeight - 1)
                        val x1 = ((ox + d.x2) * sx).toInt().coerceIn(x0 + 1, m.screenWidth)
                        val y1 = ((oy + d.y2) * sy).toInt().coerceIn(y0 + 1, m.screenHeight)
                        Rect(x0, y0, x1 - x0, y1 - y0) to fp.copyOfRange(d.row * dim, (d.row + 1) * dim)
                    }
                }
            }
        }
    }

    private fun flat(t: OnnxTensor): FloatArray = FloatArray(t.floatBuffer.remaining()).also { t.floatBuffer.get(it) }

    companion object {
        const val MODEL = "yoloe-26s-embed-top100.onnx"
        const val PE_FILE = "proposal_pe.npy"
        const val PE_ASSET = "yoloe_proposal_pe.npy"

        /** Little-endian float32 .npy (v1/v2, C order) to its flat data. */
        fun parseNpy(bytes: ByteArray): FloatArray {
            require(bytes.size > 10 && bytes[0] == 0x93.toByte() && bytes[1] == 'N'.code.toByte()) { "not npy" }
            val bb = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
            val major = bytes[6].toInt()
            val hlen = if (major == 1) bb.getShort(8).toInt() and 0xFFFF else bb.getInt(8)
            val start = (if (major == 1) 10 else 12) + hlen
            val header = String(bytes, start - hlen, hlen, Charsets.US_ASCII)
            require("<f4" in header && "'fortran_order': False" in header) { "need <f4 C-order: $header" }
            val out = FloatArray((bytes.size - start) / 4)
            bb.position(start)
            bb.asFloatBuffer().get(out)
            return out
        }

        /** (M,512) prompt rows to the graph's (8,512): repeat the last row, as runtime.pad_prompts. */
        fun padPrompts(pe: FloatArray, dim: Int = 512, n: Int = 8): FloatArray {
            val rows = pe.size / dim
            require(rows in 1..n && pe.size % dim == 0) { "proposal_pe rows=$rows" }
            return FloatArray(n * dim) { pe[minOf(it / dim, rows - 1) * dim + it % dim] }
        }
    }
}
