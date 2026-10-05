package com.veil.runtime

object ImagePrep {
    /** ARGB ints to planar CHW floats: (channel * scale - mean) / std. */
    fun nchw(argb: IntArray, w: Int, h: Int, scale: Float, mean: FloatArray, std: FloatArray): FloatArray {
        val n = w * h
        val out = FloatArray(3 * n)
        for (i in 0 until n) {
            val p = argb[i]
            out[i] = (((p shr 16) and 0xFF) * scale - mean[0]) / std[0]
            out[n + i] = (((p shr 8) and 0xFF) * scale - mean[1]) / std[1]
            out[2 * n + i] = ((p and 0xFF) * scale - mean[2]) / std[2]
        }
        return out
    }
}
