package com.veil.conductor.text

import com.veil.brain.contract.FrameMeta
import com.veil.brain.contract.Rect
import com.veil.conductor.Concepts
import com.veil.conductor.Counters
import com.veil.conductor.Frame
import com.veil.conductor.LayoutNode
import com.veil.conductor.LookInput
import com.veil.conductor.Ocr
import com.veil.conductor.TextClassifier
import org.junit.Assert.assertEquals
import org.junit.Test

class TextLaneTest {
    private val frame = Frame(FrameMeta(1, 0, 360, 780, 1080, 2340, emptyList()), ByteArray(0))
    private val post = LayoutNode("post", Rect(0, 500, 1080, 800))
    private val txt = LayoutNode("text", Rect(40, 600, 900, 100), "  You are  STUPID ")

    private fun lane(c: Counters, ocr: Ocr? = null, kw: Map<String, List<String>> = emptyMap()) = TextLane(
        Concepts(emptyList(), emptyList(), kw),
        TextClassifier { if ("stupid" in it) 0.9 else 0.0 },
        ocr,
        c
    )

    private fun input(layout: List<LayoutNode>) = LookInput(1, frame, Rect(0, 0, 1080, 2340), layout, "balanced")

    @Test
    fun toxicTextCoversWholePost() {
        val f = lane(Counters()).run(input(listOf(post, txt)))
        assertEquals(1, f.size)
        assertEquals(post.rect, f[0].rect)
        assertEquals("text.toxic", f[0].conceptId)
        assertEquals("post", f[0].scope)
    }

    @Test
    fun sameTextTwiceClassifiesOnce() {
        val c = Counters()
        val l = lane(c)
        l.run(input(listOf(post, txt)))
        l.run(input(listOf(post, txt)))
        assertEquals(1L, c.m["toxicityCalls"])
    }

    @Test
    fun ocrOnlyForImageNodes() {
        val c = Counters()
        val calls = ArrayList<Rect>()
        val img = LayoutNode("image", Rect(0, 0, 500, 500))
        lane(c, { _, r -> calls.add(r).let { null } }).run(input(listOf(post, txt, img)))
        assertEquals(listOf(img.rect), calls)
    }

    @Test
    fun keywordWholeWordHit() {
        val kw = mapOf("spoilers" to listOf("finale"))
        val t = LayoutNode("text", Rect(40, 600, 900, 100), "The FINALE was great")
        val miss = LayoutNode("text", Rect(40, 700, 900, 100), "finalest")
        val f = lane(Counters(), kw = kw).run(input(listOf(post, t, miss)))
        assertEquals(listOf("spoilers"), f.map { it.conceptId })
    }

    @Test
    fun tinyImagesSkippedAndOcrFailureDoesNotKillLane() {
        val c = Counters()
        val calls = ArrayList<Rect>()
        val tiny = LayoutNode("image", Rect(0, 0, 90, 90)) // 30 px in this 1/3-scale frame
        val ok = LayoutNode("image", Rect(0, 100, 300, 300))
        val ok2 = LayoutNode("image", Rect(0, 500, 200, 200))
        val l = lane(c, { _, r ->
            calls.add(r)
            if (r == ok.rect) error("boom") else "you are stupid"
        })
        val f = l.run(input(listOf(post, tiny, ok, ok2)))
        assertEquals(listOf(ok.rect, ok2.rect), calls)
        assertEquals(1, f.size)
    }
}
