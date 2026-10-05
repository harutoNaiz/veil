package com.veil.smoketest

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import com.veil.runtime.FloatTensor
import com.veil.runtime.ImagePrep

/** Stretches a screenshot to w x h and converts it to an NCHW float tensor. */
object Frames {
    fun tensor(path: String, w: Int, h: Int, scale: Float, mean: FloatArray, std: FloatArray): FloatTensor {
        val src = BitmapFactory.decodeFile(path) ?: error("cannot decode $path")
        val bm = Bitmap.createScaledBitmap(src, w, h, true)
        val px = IntArray(w * h)
        bm.getPixels(px, 0, w, 0, 0, w, h)
        return FloatTensor(longArrayOf(1, 3, h.toLong(), w.toLong()), ImagePrep.nchw(px, w, h, scale, mean, std))
    }
}
