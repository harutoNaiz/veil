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
    fun parsesAuto() {
        val e = """{"dim":8,"vectorF16":"AAAAAAAAAAAAAAAAAAAAAA=="}"""
        val j = one.dropLast(1) + ""","auto":{"rule":"null-quantile-v1","margin":0.0,"chips":["yak"],
            "positives":[{"term":"cats","embedding":$e,"thresholds":{"light":0.6,"balanced":0.5,"strict":0.4}}],
            "competitors":[{"term":"dog","embedding":$e,"thresholds":{"balanced":0.45}}]}}"""
        val a = ConceptPack.parse(j)[0].auto!!
        assertEquals(listOf("yak"), a.chips)
        assertEquals(0.45, a.competitors[0].thresholds["balanced"]!!, 1e-9)
        assertEquals(null, ConceptPack.parse(one)[0].auto)
    }

    @Test
    fun keywordsPicked() {
        val c = ConceptPack.toConcepts(ConceptPack.parse(one))
        assertEquals(listOf("kitten", "cat"), c.keywords["cats"])
        assertEquals(1, c.describer.size)
        assertEquals(0, c.finder.size)
    }
}
