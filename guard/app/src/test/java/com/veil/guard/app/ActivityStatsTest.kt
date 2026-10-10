package com.veil.guard.app

import com.veil.guard.overlay.Px
import java.time.LocalDate
import org.junit.Assert.assertEquals
import org.junit.Test

class ActivityStatsTest {
    @Test
    fun summarizesOneDay() {
        val all = mapOf(
            "d:2026-01-02:c:nudity" to 2,
            "d:2026-01-02:c:word" to 1,
            "d:2026-01-02:a:com.x" to 3,
            "d:2026-01-01:c:word" to 9
        )
        val s = StatsCore.summarize(all, "2026-01-02")
        assertEquals(3, s.total)
        assertEquals(listOf("com.x" to 3), StatsCore.topApps(s, 3))
    }

    @Test
    fun lastDaysAndStale() {
        val d = StatsCore.lastDays(LocalDate.parse("2026-03-02"), 3)
        assertEquals(listOf("2026-02-28", "2026-03-01", "2026-03-02"), d)
        val stale = StatsCore.stale(listOf("d:2026-02-28:c:word", "d:2026-01-01:c:word", "other"), d.toSet())
        assertEquals(listOf("d:2026-01-01:c:word"), stale)
    }

    @Test
    fun trackerCountsEachCoverOnce() {
        val t = NewCoverTracker()
        assertEquals(listOf(0), t.newOnes(listOf(Px(0, 0, 100, 100)), 0))
        assertEquals(emptyList<Int>(), t.newOnes(listOf(Px(0, 5, 100, 100)), 100))
        assertEquals(emptyList<Int>(), t.newOnes(listOf(Px(0, 300, 100, 100)), 200)) // scrolled
        assertEquals(listOf(1), t.newOnes(listOf(Px(0, 300, 100, 100), Px(500, 900, 50, 50)), 300))
        assertEquals(listOf(0), t.newOnes(listOf(Px(0, 0, 100, 100)), 5000)) // gone long ago, new again
    }
}
