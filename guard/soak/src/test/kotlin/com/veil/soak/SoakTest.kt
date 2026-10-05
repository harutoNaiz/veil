package com.veil.soak

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class SoakTest {
    private fun rows(
        pssAt: (Long) -> Long = { 100_000 },
        msAt: (Long) -> Double = { 30.0 },
        errorIndex: Int = -1
    ): List<SoakRow> = (0 until 10 * 60 * 3).map {
        val t = it * 1000L / 3
        SoakRow(t, msAt(t) + (it % 5), it != errorIndex, pssAt(t), 1, 3.0)
    }

    @Test fun fixturePasses() {
        val r = SoakAnalyzer.analyze(rows())
        assertTrue(r.toString(), r.pass)
        assertEquals(0, r.errors)
    }

    @Test fun growthSixPercentFails() {
        val r = SoakAnalyzer.analyze(rows(pssAt = { if (it > 540_000) 106_000 else 100_000 }))
        assertEquals(6.0, r.growthPct, 0.01)
        assertFalse(r.pass)
    }

    @Test fun driftTwentyFivePercentFails() {
        val r = SoakAnalyzer.analyze(rows(msAt = { if (it > 540_000) 37.5 else 30.0 }))
        assertTrue(r.toString(), r.driftPct > 20.0)
        assertFalse(r.pass)
    }

    @Test fun oneErrorFails() {
        val r = SoakAnalyzer.analyze(rows(errorIndex = 300))
        assertEquals(1, r.errors)
        assertFalse(r.pass)
    }

    @Test fun shortSoakMissingLooksFails() {
        val sparse = rows().filterIndexed { i, _ -> i % 2 == 0 }
        assertFalse(SoakAnalyzer.analyze(sparse).pass)
    }

    @Test fun timingAndParity() {
        val csv = "runtime,model,phase,i,ms\nort-qnn,look,warm,0,40\nort-qnn,look,warm,1,44\n"
        assertTrue(TimingReport.pass(TimingReport.parse(csv)))
        val a = "image,v0,v1\nx,1,0\n"
        assertEquals(1.0, FpParity.minCosine(a, a), 1e-9)
    }
}
