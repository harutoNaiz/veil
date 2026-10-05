package com.veil.conductor.regions

import com.veil.brain.cache.FingerprintCache
import com.veil.brain.contract.CompiledConcept
import com.veil.brain.contract.Embedding
import com.veil.brain.contract.FrameMeta
import com.veil.brain.contract.Rect
import com.veil.brain.cover.iouPct
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
import com.veil.conductor.Source
import java.util.Base64
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class RegionLaneTest {
    private val full = Rect(0, 0, 1080, 2400)

    private fun emb(i: Int): Embedding {
        val b = ByteArray(8)
        b[2 * i + 1] = 0x3C // half 1.0 = 0x3C00 little endian
        return Embedding(4, Base64.getEncoder().encodeToString(b))
    }

    private fun concept(id: String) = CompiledConcept(
        id,
        listOf(emb(0)),
        listOf(emb(1)),
        listOf(emb(2)),
        0.0,
        0.0,
        mapOf("light" to 0.5, "balanced" to 0.5, "strict" to 0.5),
        0.0
    )

    private fun frame(): Frame {
        val rnd = java.util.Random(7)
        val thumb = ByteArray(THUMB_W * THUMB_H) { rnd.nextInt(256).toByte() }
        return Frame(FrameMeta(1, 1000, 1080, 2400, 1080, 2400, emptyList()), thumb)
    }

    private fun input(): LookInput {
        val layout = ArrayList<LayoutNode>()
        for (i in 0 until 3) layout.add(LayoutNode("post", Rect(0, 100 + i * 700, 1080, 650)))
        layout.add(LayoutNode("image", Rect(40, 2150, 300, 200)))
        for (i in 0 until 12) {
            layout.add(LayoutNode("image", Rect((i % 3) * 360, 400 + (i / 3) * 300, 358, 298)))
        }
        layout.add(LayoutNode("web", Rect(0, 0, 1080, 2400)))
        return LookInput(1, frame(), full, layout, "balanced")
    }

    private class Fake : Describer {
        var calls = 0
        var maxBatch = 0

        override fun describe(frame: Frame, pieces: List<Piece>): List<FloatArray> {
            calls++
            maxBatch = maxOf(maxBatch, pieces.size)
            return pieces.map { floatArrayOf(1f, 0f, 0f, 0f) }
        }
    }

    private val finder = Finder { _, _ ->
        listOf(
            Rect(500, 2200, 120, 120) to floatArrayOf(1f, 0f, 0f, 0f),
            Rect(900, 50, 100, 100) to floatArrayOf(0f, 1f, 0f, 0f)
        )
    }

    @Test
    fun threeSourcesDedupedBatchedAndCached() {
        val d = Fake()
        val c = Counters()
        val lane = RegionLane(
            Concepts(listOf(concept("cat")), listOf(concept("cat")), emptyMap()),
            d,
            finder,
            FingerprintCache(),
            c
        )
        val pieces = RegionProposer().propose(input(), finder.boxes(frame(), full).map { it.first })
        assertTrue(pieces.map { it.source }.toSet().containsAll(setOf(Source.LAYOUT, Source.FINDER, Source.TILE)))
        for (i in pieces.indices) {
            for (j in i + 1 until pieces.size) {
                assertTrue(iouPct(pieces[i].rect, pieces[j].rect) < 80)
            }
        }
        assertEquals(16, pieces.count { it.source == Source.LAYOUT })

        val first = lane.run(input())
        assertTrue(first.isNotEmpty())
        assertTrue(first.any { it.lane == "finder" } && first.any { it.lane == "describer" })
        assertTrue(d.calls >= 2 && d.maxBatch <= 16)
        assertTrue(c.m.getValue("describerMaxBatch") <= 16)

        val callsBefore = d.calls
        val missesBefore = c.m.getValue("cacheMisses")
        lane.run(input())
        assertEquals(callsBefore, d.calls)
        assertEquals(missesBefore, c.m.getValue("cacheMisses"))
    }
}
