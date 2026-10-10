package com.veil.guard.capture.backup

import com.veil.guard.capture.backup.DualShotScheduler.Kind
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class DualShotSchedulerTest {
    private fun simulate(rejected: Set<Kind>, durationMs: Long = 10_000): Map<Kind, List<Long>> {
        val s = DualShotScheduler()
        val reqs = Kind.values().associateWith { mutableListOf<Long>() }
        val ok = Kind.values().associateWith { mutableListOf<Long>() }
        var now = 0L
        while (now < durationMs) {
            val (kind, delay) = s.next(now)!!
            now += delay
            if (now >= durationMs) break
            s.onRequested(kind, now)
            val prev = reqs.getValue(kind).lastOrNull()
            reqs.getValue(kind).add(now)
            // Android rule: too short if <= 333 ms after the previous request of this kind.
            if (kind in rejected || (prev != null && now - prev <= 333)) {
                s.onTooShort(kind)
            } else {
                s.onShot(kind)
                ok.getValue(kind).add(now)
            }
            now += 1 // keep time advancing even with zero delay
        }
        return ok.also { reqsCheck(reqs) }
    }

    private fun reqsCheck(reqs: Map<Kind, List<Long>>) {
        reqs.values.forEach { l -> l.zipWithNext().forEach { (a, b) -> assertTrue(b - a >= 360) } }
        val all = reqs.flatMap { (k, l) -> l.map { it to k } }.sortedBy { it.first }
        all.zipWithNext().filter { it.first.second != it.second.second }
            .forEach { (a, b) -> assertTrue(b.first - a.first >= 150) }
    }

    @Test
    fun bothKindsDoubleTheRate() {
        val ok = simulate(emptySet())
        assertTrue(ok.values.sumOf { it.size } >= 45)
    }

    @Test
    fun rejectedKindDoesNotStarveTheOther() {
        assertTrue(simulate(setOf(Kind.DISPLAY)).getValue(Kind.WINDOW).size >= 25)
        assertTrue(simulate(setOf(Kind.WINDOW)).getValue(Kind.DISPLAY).size >= 25)
    }

    @Test
    fun pausedYieldsNull() {
        val s = DualShotScheduler()
        s.pause()
        assertNull(s.next(0))
        s.resume()
        assertEquals(0L, s.next(0)!!.second)
    }
}
