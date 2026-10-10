package com.veil.conductor.regions

import org.junit.Assert.assertEquals
import org.junit.Test

/** Expected values come from workshop/forge/yoloe/runtime.py (letterbox_params, select). */
class YoloeDecodeTest {
    @Test
    fun letterboxMatchesNumpyReference() {
        fun chk(w: Int, h: Int, left: Int, top: Int) {
            val lb = YoloeDecode.letterbox(w, h)
            assertEquals("left $w x $h", left, lb.left)
            assertEquals("top $w x $h", top, lb.top)
        }
        chk(1440, 3168, 174, 0)
        chk(360, 800, 176, 0)
        chk(1080, 2400, 176, 0)
        chk(800, 600, 0, 80)
        assertEquals(0.20202020202020202, YoloeDecode.letterbox(1440, 3168).gain, 1e-12)
    }

    @Test
    fun selectMatchesNumpyReference() {
        val w = 1440
        val h = 3168
        val lb = YoloeDecode.letterbox(w, h)
        val boxes = FloatArray(400)
        val obj = FloatArray(100)
        fun put(i: Int, x1: Int, y1: Int, x2: Int, y2: Int, s: Float) {
            val v = intArrayOf(lb.left + x1, lb.top + y1, lb.left + x2, lb.top + y2)
            for (k in 0 until 4) boxes[4 * i + k] = v[k].toFloat()
            obj[i] = s
        }
        put(0, 20, 40, 200, 400, 0.9f)
        put(1, 21, 41, 201, 401, 0.8f) // NMS duplicate of 0
        put(2, 30, 300, 120, 500, 0.7f)
        put(3, 5, 5, 8, 8, 0.6f) // too small
        val d = YoloeDecode.select(boxes, obj, w, h)
        assertEquals(listOf(0, 2), d.map { it.row })
        assertEquals(0.9f, d[0].conf, 1e-6f)
        assertEquals(99f, d[0].x1, 1.5f)
        assertEquals(198f, d[0].y1, 1.5f)
        assertEquals(990f, d[0].x2, 1.5f)
        assertEquals(1980f, d[0].y2, 1.5f)
        assertEquals(148.5f, d[1].x1, 1.5f)
        assertEquals(1485f, d[1].y1, 1.5f)
        assertEquals(594f, d[1].x2, 1.5f)
        assertEquals(2475f, d[1].y2, 1.5f)
    }

    @Test
    fun confBelowThresholdAndMaxBoxes() {
        val boxes = FloatArray(400)
        val obj = FloatArray(100)
        for (i in 0 until 40) { // 40 disjoint boxes in the square (w0=h0=640, no letterbox shift)
            val x = (i % 8) * 80f
            val y = (i / 8) * 80f
            boxes[4 * i] = x
            boxes[4 * i + 1] = y
            boxes[4 * i + 2] = x + 50
            boxes[4 * i + 3] = y + 50
            obj[i] = 0.9f - i * 0.01f
        }
        obj[45] = 0.01f
        assertEquals(YoloeDecode.MAX_BOXES, YoloeDecode.select(boxes, obj, 640, 640).size)
    }
}
