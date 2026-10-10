package com.veil.guard.wire

import com.veil.brain.contract.Finding
import com.veil.brain.contract.FrameMeta
import com.veil.brain.contract.Record
import com.veil.brain.contract.Rect
import com.veil.brain.gate.THUMB_H
import com.veil.brain.gate.THUMB_W
import com.veil.conductor.AiWorker
import com.veil.conductor.Frame
import com.veil.conductor.Lane
import com.veil.conductor.OverlayPort
import java.io.File
import java.util.Random
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class LaneSwapTest {
    private val params = File("src/main/assets/params.json").readText()
    private val rnd = Random(3)
    private var clock = 1000L
    private val plans = ArrayList<Record>()
    private var factoryCalls = 0
    private var hit = false

    private val direct =
        object : AiWorker {
            override val busy = false

            override fun submit(job: () -> List<Finding>, done: (List<Finding>, Long) -> Unit) = done(job(), 1)
        }
    private val overlay =
        object : OverlayPort {
            override fun submit(plan: Record) {
                plans.add(plan)
            }

            override fun shift(dx: Int, dy: Int, tMs: Long) = Unit
        }
    private val quiet = Lane { emptyList() }
    private val loud =
        Lane {
            listOf(
                Finding(
                    "f${it.lookId}", it.frame.meta.frameId, it.lookId, it.frame.meta.tMs, "cat", 1, "hide", 0.99,
                    Rect(100, 300, 400, 400), "object", "layer1"
                )
            )
        }

    private fun core() = GuardCore(
        params, "balanced",
        {
            factoryCalls++
            listOf(if (hit) loud else quiet)
        },
        direct, { overlay }, { emptyList() }, { }, emptySet(), { clock }
    )

    private fun frame(i: Int) = Frame(
        FrameMeta(i, clock, 360, 800, 720, 1600, emptyList()),
        ByteArray(THUMB_W * THUMB_H) { if (i % 5 == 0) rnd.nextInt(256).toByte() else 100 }
    )

    private fun run(c: GuardCore, from: Int, n: Int) {
        for (i in from until from + n) {
            clock += 33
            c.offer(frame(i))
            c.pump()
        }
    }

    private fun masked() = plans.any { (it["masks"] as List<*>).isNotEmpty() }

    @Test fun swapGivesMasksWithoutRebuild() {
        val c = core()
        run(c, 0, 40)
        assertFalse(masked())
        assertEquals(1, c.buildCount)
        hit = true
        c.swapLanes()
        assertEquals(1, c.buildCount)
        run(c, 40, 80)
        assertTrue(masked())
    }

    @Test fun factoryCalledOncePerSwap() {
        val c = core()
        assertEquals(1, factoryCalls)
        c.swapLanes()
        assertEquals(2, factoryCalls)
        c.swapLanes()
        assertEquals(3, factoryCalls)
        assertEquals(1, c.buildCount)
        c.setMode("strict")
        assertEquals(2, c.buildCount)
    }

    @Test fun throwingLaneDoesNotDropOtherLanes() {
        val warns = ArrayList<Record>()
        val swap = GuardCore.SwapLane { com.veil.conductor.DebugLog { warns.add(it) } }
        val bad = Lane { throw ArrayIndexOutOfBoundsException("length=8 index=8") }
        swap.current = listOf(bad, loud, bad)
        val input = com.veil.conductor.LookInput(1, frame(1), Rect(0, 0, 10, 10), emptyList(), "balanced")
        val out = swap.run(input)
        assertEquals(1, out.size)
        assertEquals("layer1", out[0].lane)
        assertEquals(2, warns.count { it["what"] == "lane-failed" })
    }
}
