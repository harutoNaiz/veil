package com.veil.brain.unit

import com.veil.brain.contract.FrameMeta
import com.veil.brain.contract.UiEvent
import com.veil.brain.gate.Change
import com.veil.brain.gate.Gatekeeper
import com.veil.brain.gate.ModeParams
import com.veil.brain.gate.SchedState
import com.veil.brain.gate.Scheduler
import com.veil.brain.gate.Tick
import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class GateTests {
    private val blank = ByteArray(32 * 64) { 100 }

    @Test
    fun shiftRowsRounds() {
        assertEquals(0, Change.shiftRows(0, 100, 200, 100))
        assertEquals(16, Change.shiftRows(50, 100, 200, 100))
        assertEquals(-16, Change.shiftRows(-50, 100, 200, 100))
    }

    @Test
    fun detectNoRefAndCut() {
        val first = Change.detect(blank, null, 0)
        assertEquals(32, first.changedTiles)
        val white = ByteArray(32 * 64) { 255.toByte() }
        assertTrue(Change.detect(white, blank, 0).sceneCut)
        val same = Change.detect(blank, blank, 0)
        assertEquals(0, same.changedTiles)
        assertNull(same.changedBox)
    }

    @Test
    fun detectScrollRevealsStrip() {
        val r = Change.detect(blank, blank, 8)
        assertEquals(Pair(2, 10), r.revealedRows)
        assertEquals(255, r.tileScores[0])
    }

    @Test
    fun schedulerCheckupThenImmediate() {
        val p = ModeParams(3, 5000, 150)
        val (s1, r1) = Scheduler.step(SchedState(), Tick(0, 1, 100, 200), p)
        assertEquals("checkup", r1!!.why)
        val (s2, r2) = Scheduler.step(s1, Tick(10, 2, 100, 200, sceneCut = true), p)
        assertEquals("sceneCut", r2!!.why)
        val (s3, r3) = Scheduler.step(s2, Tick(100, 3, 100, 200, sceneCut = true), p)
        assertNull(r3)
        val (_, r4) = Scheduler.step(s3, Tick(200, 4, 100, 200), p)
        assertEquals("sceneCut", r4!!.why)
        assertEquals(3, Scheduler.cdiv(5, 2))
        assertEquals("sceneCut", Scheduler.better("swipe", "sceneCut"))
    }

    @Test
    fun gatekeeperFromParams() {
        val json = File(System.getProperty("veil.repo"), "workshop/twin/params.json").readText()
        val g = Gatekeeper.create("balanced", json, 0)
        g.onEvent(UiEvent("windowChanged", 0, packageName = "a.b"))
        val (change, look) = g.onThumb(blank, FrameMeta(1, 0, 100, 200, 100, 200, emptyList()))
        assertEquals("change", change["kind"])
        assertNotNull(look["rect"])
        assertEquals(listOf("kind", "frameId", "tMs", "look", "reason", "state", "x", "rect"), look.keys.toList())
    }
}
