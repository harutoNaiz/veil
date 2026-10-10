package com.veil.conductor.regions

/** Pure port of workshop/forge/yoloe/runtime.py: square letterbox maths, un-letterbox, MIN_SIDE, class-agnostic NMS. */
object YoloeDecode {
    const val SIZE = 640
    const val PAD = 114
    const val CONF = 0.05f
    const val IOU = 0.5
    const val MAX_BOXES = 20
    const val MIN_SIDE = 24

    /** Centred square letterbox (Ultralytics rounding): resized w/h, pad left/top. */
    class Lb(val gain: Double, val newW: Int, val newH: Int, val left: Int, val top: Int)

    class Det(val x1: Float, val y1: Float, val x2: Float, val y2: Float, val conf: Float, val row: Int)

    fun letterbox(w0: Int, h0: Int): Lb {
        val gain = minOf(SIZE.toDouble() / h0, SIZE.toDouble() / w0)
        val nw = Math.rint(w0 * gain).toInt()
        val nh = Math.rint(h0 * gain).toInt()
        val dw = (SIZE - nw) / 2.0
        val dh = (SIZE - nh) / 2.0
        return Lb(gain, nw, nh, Math.rint(dw - 0.1).toInt(), Math.rint(dh - 0.1).toInt())
    }

    private fun iou(a: Det, b: Det): Double {
        val w = minOf(a.x2, b.x2) - maxOf(a.x1, b.x1)
        val h = minOf(a.y2, b.y2) - maxOf(a.y1, b.y1)
        val inter = if (w <= 0 || h <= 0) 0.0 else w.toDouble() * h
        val aa = maxOf(a.x2 - a.x1, 0f).toDouble() * maxOf(a.y2 - a.y1, 0f)
        val ab = maxOf(b.x2 - b.x1, 0f).toDouble() * maxOf(b.y2 - b.y1, 0f)
        return inter / maxOf(aa + ab - inter, 1e-12)
    }

    /**
     * boxes: n*4 xyxy in the 640 square; obj: n scores. Result in original (w0,h0) px, best score first,
     * filtered by CONF, MIN_SIDE, NMS and MAX_BOXES.
     */
    fun select(boxes: FloatArray, obj: FloatArray, w0: Int, h0: Int): List<Det> {
        val lb = letterbox(w0, h0)
        val cand = ArrayList<Det>()
        for (i in obj.indices) {
            if (obj[i] < CONF) continue
            val x1 = ((boxes[4 * i] - lb.left) / lb.gain).toFloat().coerceIn(0f, w0.toFloat())
            val y1 = ((boxes[4 * i + 1] - lb.top) / lb.gain).toFloat().coerceIn(0f, h0.toFloat())
            val x2 = ((boxes[4 * i + 2] - lb.left) / lb.gain).toFloat().coerceIn(0f, w0.toFloat())
            val y2 = ((boxes[4 * i + 3] - lb.top) / lb.gain).toFloat().coerceIn(0f, h0.toFloat())
            if (x2 - x1 >= MIN_SIDE && y2 - y1 >= MIN_SIDE) cand.add(Det(x1, y1, x2, y2, obj[i], i))
        }
        val order = cand.sortedByDescending { it.conf } // stable, like np.argsort(kind="stable") on -score
        val keep = ArrayList<Det>()
        for (d in order) {
            if (keep.size >= MAX_BOXES) break
            if (keep.none { iou(it, d) > IOU }) keep.add(d)
        }
        return keep
    }
}
