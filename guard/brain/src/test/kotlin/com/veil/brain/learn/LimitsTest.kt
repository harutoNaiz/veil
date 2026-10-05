package com.veil.brain.learn

import com.veil.brain.contract.CompiledConcept
import com.veil.brain.contract.Verdict
import org.junit.Assert.assertEquals
import org.junit.Assert.assertSame
import org.junit.Assert.assertTrue
import org.junit.Test

class LimitsTest {
    private fun vec(i: Int) = DoubleArray(32).also {
        it[i % 32] = 1.0
        it[(i * 7 + 1) % 32] += 0.5 + i * 0.01
    }

    private fun cc(id: String) = CompiledConcept(id, emptyList(), emptyList(), emptyList(), 0.0, 0.0, emptyMap(), 0.0)

    private val hide = Verdict(1.0, 1.0, 1.0, 1.0, "hide")

    @Test
    fun exceptionsBounded() {
        val b = CorrectionBook()
        for (i in 0 until 70) b.record(Feedback("notThis", "cat"), vec(i))
        assertEquals(CorrectionBook.MAX_EXCEPTIONS, b.exceptionCount("cat"))
    }

    @Test
    fun nudgeCaps() {
        val up = CorrectionBook()
        val down = CorrectionBook()
        repeat(10) {
            up.record(Feedback("notThis", "cat"), null)
            down.record(Feedback("missed", "cat"), null)
        }
        assertEquals(0.15, up.nudgeOf("cat"), 1e-9)
        assertEquals(-0.15, down.nudgeOf("cat"), 1e-9)
        assertEquals(-0.15, up.adjust(cc("cat")).userOffset, 1e-9)
    }

    @Test
    fun layer1IsUntouched() {
        val b = CorrectionBook()
        val r = runCatching { b.record(Feedback("notThis", "cat", layer = 1), vec(0)) }
        assertTrue(r.isFailure)
        assertTrue(runCatching { b.record(Feedback("notThis", "nsfw"), vec(0)) }.isFailure)
        val c = cc("nsfw")
        assertSame(c, b.adjust(c))
        assertSame(hide, b.filter("nsfw", vec(0), hide))
    }

    @Test
    fun filterAndRoundTrip() {
        val b = CorrectionBook()
        b.record(Feedback("notThis", "cat"), vec(3))
        assertEquals("leave", b.filter("cat", vec(3), hide).decision)
        assertEquals("hide", b.filter("cat", vec(12), hide).decision)
        val b2 = CorrectionBook.fromJson(b.toJson())
        assertEquals("leave", b2.filter("cat", vec(3), hide).decision)
    }
}
