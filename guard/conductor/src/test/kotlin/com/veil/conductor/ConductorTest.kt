package com.veil.conductor

import com.veil.brain.contract.FrameMeta
import com.veil.brain.contract.Record
import com.veil.brain.contract.UiEvent
import com.veil.brain.gate.THUMB_H
import com.veil.brain.gate.THUMB_W
import java.io.File
import java.util.Random
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ConductorTest {
    private val params = File(System.getProperty("veil.repo"), "workshop/twin/params.json").readText()
    private val rnd = Random(7)

    private class Rig(params: String, val worker: ManualWorker, skip: Set<String> = setOf("com.skip.app")) {
        val overlay = RecordingOverlay()
        val stats = ArrayList<Record>()
        val looks = ArrayList<Record>()
        val c =
            Conductor(
                "balanced", params, listOf(ScriptedLane()), worker, overlay, { stats.add(it) },
                { if (it["kind"] == "look") looks.add(it).also { worker.tag = looks.size } }, Counters(), skip,
                { emptyList() }
            )
    }

    private fun frame(i: Int, t: Long, noise: Boolean) = Frame(
        FrameMeta(i, t, 360, 800, 720, 1600, emptyList()),
        ByteArray(THUMB_W * THUMB_H) { if (noise) rnd.nextInt(256).toByte() else 100 }
    )

    @Test fun neverQueues() {
        val w = ManualWorker()
        val r = Rig(params, w)
        for (i in 0 until 600) {
            val t = 1000L + i * 16
            w.now = t
            w.completeDue(t, 300)
            r.c.offer(frame(i, t, i % 7 == 0))
            r.c.pump()
        }
        assertTrue(w.maxPending <= 1)
        assertTrue(r.looks.isNotEmpty())
        val last = r.stats.last()
        assertTrue((last["framesSkippedBusy"] as Int) > 0)
        assertTrue(r.stats.isNotEmpty())
    }

    @Test fun pausedMeansNoLooks() {
        for (e in listOf(UiEvent("screenOff", 900), UiEvent("windowChanged", 900, packageName = "com.skip.app"))) {
            val r = Rig(params, ManualWorker(true))
            r.c.onEvent(e)
            for (i in 0 until 30) {
                r.c.offer(frame(i, 1000L + i * 33, true))
                r.c.pump()
            }
            assertTrue(r.c.paused)
            assertEquals(0, r.looks.size)
            assertEquals("clear", (r.overlay.plans.last()["reason"]))
        }
    }

    @Test fun scrollShiftsImmediately() {
        val r = Rig(params, ManualWorker(true))
        r.c.offer(frame(0, 1000, false))
        r.c.pump()
        r.c.onEvent(UiEvent("scrolled", 1010, dy = -20, packageName = "com.a"))
        assertEquals("shift", r.overlay.calls.last())
        r.c.offer(frame(1, 1033, false))
        r.c.pump()
        assertEquals("plan", r.overlay.calls.last())
    }

    @Test fun statsAfterEachLook() {
        val w = ManualWorker()
        val r = Rig(params, w)
        r.c.offer(frame(0, 1000, false))
        r.c.pump()
        assertEquals(1, w.pending.size)
        w.complete(w.pending[0], 42)
        assertEquals(1, r.stats.size)
        assertEquals(42L, r.stats[0]["aiMsLast"])
        assertEquals(1, r.stats[0]["looksTotal"])
    }
}
