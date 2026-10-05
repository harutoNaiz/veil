package com.veil.conductor.text

import org.junit.Assert.assertEquals
import org.junit.Test

class ToxPrepTest {
    @Test
    fun padsAndMasks() {
        val (x, m) = ToxPrep.inputs(intArrayOf(2, 5, 1), 6, 0)
        assertEquals(listOf(2L, 5L, 1L, 0L, 0L, 0L), x.toList())
        assertEquals(listOf(1L, 1L, 1L, 0L, 0L, 0L), m.toList())
    }

    @Test
    fun truncatesAt128() {
        val (x, m) = ToxPrep.inputs(IntArray(200) { it + 1 }, 128, 0)
        assertEquals(128, x.size)
        assertEquals(128L, x[127])
        assertEquals(128L, m.sum())
    }

    @Test
    fun scoreHalfAtZero() {
        assertEquals(0.5, ToxPrep.score(floatArrayOf(0f, 3f, 1f)), 0.0)
    }
}
