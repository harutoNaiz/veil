package com.veil.guard.wire.ml

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class OrtFinderTest {
    @Test
    fun bundledProposalPeParsesAsEightByFiveTwelve() {
        val f = listOf("src/main/assets/yoloe_proposal_pe.npy", "app/src/main/assets/yoloe_proposal_pe.npy")
            .map { File(it) }.first { it.isFile }
        val pe = OrtFinder.padPrompts(OrtFinder.parseNpy(f.readBytes()))
        assertEquals(8 * 512, pe.size)
        val n = Math.sqrt((0 until 512).sumOf { (pe[it] * pe[it]).toDouble() })
        assertEquals(1.0, n, 1e-3)
    }

    @Test
    fun padRepeatsLastRow() {
        val pe = FloatArray(3 * 4) { (it / 4).toFloat() }
        val out = OrtFinder.padPrompts(pe, dim = 4, n = 8)
        assertEquals(32, out.size)
        assertTrue((16 until 32).all { out[it] == 2f })
    }
}
