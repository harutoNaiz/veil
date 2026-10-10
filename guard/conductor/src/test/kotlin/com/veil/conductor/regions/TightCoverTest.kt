package com.veil.conductor.regions

import com.veil.brain.cache.FingerprintCache
import com.veil.brain.contract.CompiledConcept
import com.veil.brain.contract.Embedding
import com.veil.brain.contract.FrameMeta
import com.veil.brain.contract.Rect
import com.veil.brain.gate.THUMB_H
import com.veil.brain.gate.THUMB_W
import com.veil.conductor.Concepts
import com.veil.conductor.Counters
import com.veil.conductor.Describer
import com.veil.conductor.Finder
import com.veil.conductor.Frame
import com.veil.conductor.LayoutNode
import com.veil.conductor.LookInput
import com.veil.conductor.Piece
import java.util.Base64
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class TightCoverTest {
    private val sw = 1440
    private val sh = 3168
    private val cat = Rect(300, 1200, 500, 450)

    private fun emb(i: Int): Embedding {
        val b = ByteArray(8)
        b[2 * i + 1] = 0x3C
        return Embedding(4, Base64.getEncoder().encodeToString(b))
    }

    private val concept = CompiledConcept(
        "cats",
        listOf(emb(0)),
        listOf(emb(1)),
        listOf(emb(2)),
        0.0,
        0.0,
        mapOf("light" to 0.5, "balanced" to 0.5, "strict" to 0.5),
        0.0
    )

    private fun overlaps(a: Rect, b: Rect) = a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h

    /** Says "cat" for any crop that touches the cat, "nothing" otherwise. */
    private val describer = object : Describer {
        override fun describe(frame: Frame, pieces: List<Piece>) = pieces.map {
            if (overlaps(it.rect, cat)) floatArrayOf(1f, 0f, 0f, 0f) else floatArrayOf(0f, 0f, 0f, 1f)
        }
    }

    private fun input(argb: IntArray?, flat: Boolean = false): LookInput {
        val rnd = java.util.Random(3)
        val thumb = ByteArray(THUMB_W * THUMB_H) { if (flat) 90 else rnd.nextInt(256).toByte() }
        val meta = FrameMeta(1, 1000, sw, sh, sw, sh, emptyList())
        val layout = listOf(LayoutNode("image", Rect(0, 0, sw, sh)))
        return LookInput(1, Frame(meta, thumb, argb), Rect(0, 0, sw, sh), layout, "balanced")
    }

    private fun lane(finder: Finder?) = RegionLane(
        Concepts(listOf(concept), emptyList(), emptyMap()),
        describer,
        finder,
        FingerprintCache(),
        Counters()
    )

    @Test
    fun finderBoxWinsOverFullScreenAndTiles() {
        val f = Finder { _, _ -> listOf(cat to FloatArray(4)) }
        val findings = lane(f).run(input(null))
        assertTrue(findings.any { it.rect == cat })
        val grown = Rect(cat.x - 75, cat.y - 68, cat.w + 150, cat.h + 136) // cat grown 15% per side
        for (f in findings) {
            assertTrue("$f", f.rect.x >= grown.x && f.rect.y >= grown.y)
            assertTrue("$f", f.rect.x + f.rect.w <= grown.x + grown.w && f.rect.y + f.rect.h <= grown.y + grown.h)
        }
    }

    @Test
    fun flatFrameNeverHides() {
        val f = Finder { _, _ -> listOf(cat to FloatArray(4)) }
        assertTrue(lane(f).run(input(null, flat = true)).none { it.decision == "hide" })
    }

    @Test
    fun containerWithRelatedFinderThatDoesNotHideStaysDown() {
        // finder box on the cat overlaps the tiles, but it looks like "nothing": tile hits are vetoed by agree
        val miss = Rect(cat.x, cat.y, 120, 120)
        val f = Finder { _, _ -> listOf(miss to FloatArray(4)) }
        val l = RegionLane(
            Concepts(listOf(concept), emptyList(), emptyMap()),
            object : Describer {
                override fun describe(frame: Frame, pieces: List<Piece>) = pieces.map {
                    if (it.rect == miss) floatArrayOf(0f, 0f, 0f, 1f) else floatArrayOf(1f, 0f, 0f, 0f)
                }
            },
            f,
            FingerprintCache(),
            Counters()
        )
        val out = l.run(input(null))
        assertTrue(out.none { it.decision == "hide" && it.rect.w > 400 && overlaps(it.rect, miss) && it.rect.w < sw })
    }

    @Test
    fun withoutFinderCoarsePiecesRemainAsFallback() {
        val findings = lane(null).run(input(null))
        assertTrue(findings.any { it.rect.w * it.rect.h > sw * sh / 4 })
    }

    @Test
    fun letterboxBarsAreTrimmedFromLayoutNode() {
        // photo occupies y in 600..2400, black bars above/below, nodes spans the full screen
        val argb = IntArray(sw * sh) { i ->
            val y = i / sw
            if (y in 600 until 2400) 0xFF808080.toInt() else 0xFF000000.toInt()
        }
        val ps = RegionProposer().propose(input(argb), emptyList())
        val l = ps.first { it.id == "L0" }
        assertEquals(600, l.rect.y)
        assertEquals(1800, l.rect.h)
        assertEquals(sw, l.rect.w)
    }
}
