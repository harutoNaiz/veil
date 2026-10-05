package com.veil.conductor

import com.veil.brain.gate.THUMB_H
import com.veil.brain.gate.THUMB_W

object Thumbs {
    /** Port of twin change.py thumb: BGR2GRAY then INTER_AREA resize to THUMB_W x THUMB_H. */
    fun fromArgb(argb: IntArray, w: Int, h: Int): ByteArray {
        val gray =
            IntArray(w * h) {
                val p = argb[it]
                val r = (p shr 16) and 255
                val g = (p shr 8) and 255
                val b = p and 255
                (r * 4899 + g * 9617 + b * 1868 + 8192) shr 14
            }
        val out = ByteArray(THUMB_W * THUMB_H)
        val sx = w.toDouble() / THUMB_W
        val sy = h.toDouble() / THUMB_H
        for (dy in 0 until THUMB_H) {
            val y0 = dy * sy
            val y1 = y0 + sy
            for (dx in 0 until THUMB_W) {
                val x0 = dx * sx
                val x1 = x0 + sx
                var acc = 0.0
                var yy = y0.toInt()
                while (yy < y1 && yy < h) {
                    val wy = minOf(yy + 1.0, y1) - maxOf(yy.toDouble(), y0)
                    var xx = x0.toInt()
                    while (xx < x1 && xx < w) {
                        val wx = minOf(xx + 1.0, x1) - maxOf(xx.toDouble(), x0)
                        acc += gray[yy * w + xx] * wx * wy
                        xx++
                    }
                    yy++
                }
                out[dy * THUMB_W + dx] = Math.round(acc / (sx * sy)).toInt().coerceIn(0, 255).toByte()
            }
        }
        return out
    }
}
