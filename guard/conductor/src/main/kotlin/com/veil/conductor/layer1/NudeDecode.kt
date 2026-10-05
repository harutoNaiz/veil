package com.veil.conductor.layer1

import com.veil.brain.contract.Rect
import com.veil.conductor.NsfwBox
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

/** Port of workshop/forge/nudenet/decode.py. raw is channel-major: (4+c) rows of n values. */
object NudeDecode {
    fun decode(
        raw: FloatArray,
        n: Int,
        c: Int,
        conf: Float,
        iou: Float,
        lb: Triple<Float, Float, Float>
    ): List<NsfwBox> {
        class Cand(val cls: Int, val score: Float, val b: FloatArray)
        val (scale, px, py) = lb
        val cands = ArrayList<Cand>()
        for (i in 0 until n) {
            var best = 0
            var bs = Float.NEGATIVE_INFINITY
            for (k in 0 until c) {
                val s = raw[(4 + k) * n + i]
                if (s > bs) {
                    bs = s
                    best = k
                }
            }
            if (bs < conf) continue
            val cx = raw[i]
            val cy = raw[n + i]
            val w = raw[2 * n + i]
            val h = raw[3 * n + i]
            cands.add(
                Cand(
                    best,
                    bs,
                    floatArrayOf(
                        (cx - w / 2 - px) / scale,
                        (cy - h / 2 - py) / scale,
                        (cx + w / 2 - px) / scale,
                        (cy + h / 2 - py) / scale
                    )
                )
            )
        }
        val out = ArrayList<Cand>()
        for (cls in cands.map { it.cls }.distinct()) {
            val order = cands.filter { it.cls == cls }.sortedByDescending { it.score }.toMutableList()
            while (order.isNotEmpty()) {
                val a = order.removeAt(0)
                out.add(a)
                order.removeAll { iouF(a.b, it.b) > iou }
            }
        }
        return out.sortedByDescending { it.score }.map {
            val x1 = it.b[0].roundToInt()
            val y1 = it.b[1].roundToInt()
            NsfwBox(it.cls, it.score, Rect(x1, y1, it.b[2].roundToInt() - x1, it.b[3].roundToInt() - y1))
        }
    }

    private fun iouF(a: FloatArray, b: FloatArray): Float {
        val iw = max(0f, min(a[2], b[2]) - max(a[0], b[0]))
        val ih = max(0f, min(a[3], b[3]) - max(a[1], b[1]))
        val inter = iw * ih
        val u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
        return inter / max(u, 1e-9f)
    }
}
