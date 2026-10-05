package com.veil.guard.wire.ml

import org.junit.Assert.assertEquals
import org.junit.Test

class ConceptPackTest {
    private val one =
        """{"conceptId":"cats","looksLike":[{"dim":8,"vectorF16":"AAAAAAAAAAAAAAAAAAAAAA=="}],
        "thresholds":{"light":0.6,"balanced":0.5,"strict":0.4},"margin":0.05,"keywords":["kitten","cat"]}"""

    @Test
    fun parsesSingleAndPack() {
        val a = ConceptPack.parse(one)
        assertEquals(1, a.size)
        assertEquals("cats", a[0].conceptId)
        assertEquals(8, a[0].looksLike[0].dim)
        assertEquals(2, ConceptPack.parse("""{"concepts":[$one,$one]}""").size)
    }

    @Test
    fun keywordsPicked() {
        val c = ConceptPack.toConcepts(ConceptPack.parse(one))
        assertEquals(listOf("kitten", "cat"), c.keywords["cats"])
        assertEquals(1, c.describer.size)
        assertEquals(0, c.finder.size)
    }
}
