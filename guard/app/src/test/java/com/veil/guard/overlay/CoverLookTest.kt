package com.veil.guard.overlay

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class CoverLookTest {
    @Test
    fun categories() {
        assertEquals("nudity", CoverLook.category(1, emptyList()))
        assertEquals("sexual", CoverLook.category(2, listOf("sexual", "sexual")))
        assertEquals("word", CoverLook.category(2, listOf("", null)))
        assertEquals("mixed", CoverLook.category(2, listOf("violence", "politics")))
    }

    @Test
    fun childNeverHintsAtSensitiveIcons() {
        assertEquals("heart", CoverLook.icon("sexual", false))
        assertEquals("eye", CoverLook.icon("sexual", true))
        assertEquals("eye", CoverLook.icon("violence", true))
        assertEquals("flag", CoverLook.icon("politics", true))
        assertEquals("eye", CoverLook.icon("mixed", false))
    }

    @Test
    fun wording() {
        val adult = CoverLook.texts("Violence & gore", true, false)
        assertEquals("Sensitive content" to "May contain violence & gore", adult)
        assertEquals("Hidden for you" to "Not for kids", CoverLook.texts("", false, true))
        assertEquals("Hidden for you" to "Political content", CoverLook.texts("Political content", false, true))
    }

    @Test
    fun bigRule() {
        assertTrue(CoverLook.isBig(200, 1000))
        assertFalse(CoverLook.isBig(199, 1000))
    }
}
