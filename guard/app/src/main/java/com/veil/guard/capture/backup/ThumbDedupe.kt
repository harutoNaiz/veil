package com.veil.guard.capture.backup

/** Pure: 32x64 luma checksum so unchanged screenshots are dropped ("only when changed"). */
class ThumbDedupe {
    private var last: Long? = null

    fun checksum(luma: ByteArray, w: Int, h: Int): Long {
        var hash = 1469598103934665603L
        for (ty in 0 until THUMB_H) {
            val y = ty * h / THUMB_H
            for (tx in 0 until THUMB_W) {
                val x = tx * w / THUMB_W
                hash = (hash xor (luma[y * w + x].toLong() and 0xFF)) * 1099511628211L
            }
        }
        return hash
    }

    /** True when the frame differs from the previous one (and remembers it). */
    fun changed(luma: ByteArray, w: Int, h: Int): Boolean {
        val c = checksum(luma, w, h)
        val isNew = last != c
        last = c
        return isNew
    }

    fun reset() {
        last = null
    }

    private companion object {
        const val THUMB_W = 32
        const val THUMB_H = 64
    }
}
