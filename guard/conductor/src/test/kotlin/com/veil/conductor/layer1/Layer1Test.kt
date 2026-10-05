package com.veil.conductor.layer1

import com.veil.brain.contract.FrameMeta
import com.veil.brain.contract.Rect
import com.veil.brain.motion.BrainPipeline
import com.veil.conductor.Counters
import com.veil.conductor.Frame
import com.veil.conductor.LookInput
import com.veil.conductor.NsfwBox
import com.veil.conductor.NsfwDetector
import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class Layer1Test {
    private val meta = FrameMeta(1, 0, 360, 780, 1080, 2340, emptyList())
    private val frame = Frame(meta, ByteArray(0))
    private val area = Rect(0, 0, 1080, 2340)

    private class Fake(override val id: String, val boxes: List<NsfwBox>) : NsfwDetector {
        override fun detect(frame: Frame, area: Rect) = boxes
    }

    private fun input(mode: String) = LookInput(1, frame, area, emptyList(), mode)

    @Test
    fun smallOnlyInLightBothInBalanced() {
        val c = Counters()
        val lane = Layer1Lane(Fake("320n", emptyList()), Fake("640m", emptyList()), c)
        lane.run(input("light"))
        assertEquals(null, c.m["layer1.640m"])
        lane.run(input("balanced"))
        assertEquals(1L, c.m["layer1.640m"])
        assertEquals(2L, c.m["layer1.320n"])
    }

    @Test
    fun mergesAndFiltersClasses() {
        val r = Rect(100, 100, 200, 200)
        val small = Fake("320n", listOf(NsfwBox(3, 0.8f, r), NsfwBox(1, 0.99f, Rect(0, 0, 50, 50))))
        val large = Fake("640m", listOf(NsfwBox(3, 0.9f, Rect(105, 105, 200, 200))))
        val f = Layer1Lane(small, large, Counters()).run(input("strict"))
        assertEquals(1, f.size)
        assertEquals(1, f[0].layer)
    }

    @Test
    fun layer1PlanIsSolidNonPeekableOnFirstLook() {
        val params = File(System.getProperty("veil.repo"), "workshop/twin/params.json").readText()
        val pipe = BrainPipeline("balanced", params)
        val thumb = ByteArray(0)
        val box = Rect(200, 600, 400, 400)
        val f = Layer1Lane(Fake("320n", listOf(NsfwBox(3, 0.9f, box))), null, Counters()).run(input("balanced"))
        assertEquals(1, f.size)
        pipe.enqueue(f[0])
        var masks: List<Map<*, *>> = emptyList()
        for (t in 0..2) {
            val g = ByteArray(com.veil.brain.gate.THUMB_W * com.veil.brain.gate.THUMB_H) { 100 }
            val out = pipe.step(g, meta.copy(frameId = 2 + t, tMs = 100L * (t + 1)))

            @Suppress("UNCHECKED_CAST")
            val plan = out.last()["plan"] as Map<String, Any?>
            @Suppress("UNCHECKED_CAST")
            masks = plan["masks"] as List<Map<*, *>>
        }
        assertTrue(masks.isNotEmpty())
        assertEquals("solid", masks[0]["style"])
        assertFalse(masks[0]["peekable"] as Boolean)
        thumb.size
    }

    @Test
    fun decodeHandMadeArray() {
        // n=3 anchors, c=2 classes: rows cx,cy,w,h,s0,s1
        val raw = floatArrayOf(
            50f, 52f, 200f, // cx
            50f, 52f, 200f, // cy
            20f, 20f, 10f, // w
            20f, 20f, 10f, // h
            0.9f, 0.8f, 0.1f, // class 0
            0.1f, 0.1f, 0.7f // class 1
        )
        val out = NudeDecode.decode(raw, 3, 2, 0.5f, 0.45f, Triple(0.5f, 0f, 0f))
        assertEquals(2, out.size)
        assertEquals(0, out[0].cls)
        assertEquals(Rect(80, 80, 40, 40), out[0].rect)
    }
}
