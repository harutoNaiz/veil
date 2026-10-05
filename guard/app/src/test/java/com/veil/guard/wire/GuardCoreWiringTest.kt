package com.veil.guard.wire

import com.veil.brain.contract.Finding
import com.veil.brain.contract.FrameMeta
import com.veil.brain.contract.Record
import com.veil.brain.contract.Rect
import com.veil.brain.contract.UiEvent
import com.veil.brain.gate.THUMB_H
import com.veil.brain.gate.THUMB_W
import com.veil.conductor.AiWorker
import com.veil.conductor.Frame
import com.veil.conductor.Lane
import com.veil.conductor.OverlayPort
import java.io.File
import java.util.Random
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class GuardCoreWiringTest {
    private val params = File("src/main/assets/params.json").readText()
    private val rnd = Random(3)
    private var clock = 1000L
    private val logs = ArrayList<Record>()
    private val plans = ArrayList<Record>()
    private val calls = ArrayList<String>()

    private val direct =
        object : AiWorker {
            override val busy = false

            override fun submit(job: () -> List<Finding>, done: (List<Finding>, Long) -> Unit) = done(job(), 1)
        }
    private val overlay =
        object : OverlayPort {
            override fun submit(plan: Record) {
                plans.add(plan)
                calls.add("plan")
            }

            override fun shift(dx: Int, dy: Int, tMs: Long) {
                calls.add("shift")
            }
        }
    private val lane =
        Lane {
            listOf(
                Finding(
                    "f${it.lookId}", it.frame.meta.frameId, it.lookId, it.frame.meta.tMs, "cat", 1, "hide", 0.99,
                    Rect(100, 300, 400, 400), "object", "layer1"
                )
            )
        }

    private fun core(mode: String = "balanced") =
        GuardCore(
            params, mode, { listOf(lane) }, direct, { overlay }, { emptyList() }, { logs.add(it) }, emptySet(),
            { clock }
        )

    private fun frame(i: Int) =
        Frame(
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

    private fun looks() = logs.count { it["kind"] == "look" }

    @Test fun plansAndStages() {
        val c = core()
        run(c, 0, 80)
        assertTrue(plans.any { (it["masks"] as List<*>).isNotEmpty() })
        c.onDrawn(clock + 1)
        val st = logs.filter { it["kind"] == "stage" }
        val ids = st.map { it["lookId"] as Int }.distinct()
        val full = ids.first { id -> st.filter { it["lookId"] == id }.map { it["stage"] }.contains("draw") }
        val mine = st.filter { it["lookId"] == full }
        assertEquals(listOf("frame", "gate", "ai", "judge", "plan", "draw"), mine.map { it["stage"] })
        val ts = mine.map { (it["tMs"] as Number).toLong() }
        assertEquals(ts.sorted(), ts)
    }

    @Test fun planLinesHaveBothShapes() {
        val c = core()
        run(c, 0, 80)
        val enc = JsonlDebugLog.encode(logs.first { it["kind"] == "plan" })
        val pl = logs.first { it["kind"] == "plan" }
        assertTrue(enc.contains("\"plan\":{"))
        assertTrue(enc.contains("\"masks\":["))
        // wrapping happens in JsonlDebugLog: feed it and read the line back
        val lines = ArrayList<String>()
        JsonlDebugLog { lines.add(it) }.write(pl)
        assertTrue(Regex("\"masks\":\\[\\{[^]]*\"rect\":\\[\\d+,\\d+,\\d+,\\d+]").containsMatchIn(lines[0]))
        assertTrue(lines[0].contains("\"plan\":{"))
    }

    @Test fun strictKeepsPlanning() {
        val c = core()
        run(c, 0, 20)
        c.setMode("strict")
        plans.clear()
        run(c, 20, 80)
        assertEquals("strict", c.mode)
        assertTrue(plans.isNotEmpty())
    }

    @Test fun pauseStopsLooks() {
        val c = core()
        run(c, 0, 20)
        val before = looks()
        plans.clear()
        c.pause()
        run(c, 20, 40)
        assertEquals(before, looks())
        assertEquals(1, plans.size)
        assertTrue((plans[0]["masks"] as List<*>).isEmpty())
    }

    @Test fun scrollShifts() {
        val c = core()
        run(c, 0, 3)
        c.onEvent(UiEvent("scrolled", clock, dy = -20, packageName = "com.a"))
        assertEquals("shift", calls.last())
    }
}
