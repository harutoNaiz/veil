package com.veil.teacher

import com.veil.teacher.autocal.AutoCal
import kotlin.math.abs
import kotlin.math.sqrt
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class AutoCalOovTest {
    private class Fake : TextEncoder {
        val seen = ArrayList<String>()
        override val spaceId = "siglip2-base-p16-224"
        override val textModelId = "siglip2-base-text"
        override fun encode(phrases: List<String>): List<FloatArray> = phrases.map { p ->
            seen.add(p)
            FloatArray(4) { i -> (p.length + i * 3).toFloat() }
        }
    }

    @Test
    fun ensembleUsesAllTemplatesAndIsUnit() {
        val f = Fake()
        val e = AutoCal.ensemble("Origami  Cranes", f)
        assertEquals(AutoCal.TEMPLATES.map { it.replace("{w}", "origami crane") }, f.seen)
        assertEquals(1.0, sqrt(e.sumOf { it * it }), 1e-9)
        assertTrue(e.all { abs(it) <= 1.0 })
    }
}
