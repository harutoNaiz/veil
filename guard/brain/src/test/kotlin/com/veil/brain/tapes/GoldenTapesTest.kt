package com.veil.brain.tapes

import java.io.File
import org.junit.Assert.assertNull
import org.junit.Test

class GoldenTapesTest {
    private val dir = File(System.getProperty("veil.tapes"))
    private val params = File(System.getProperty("veil.repo"), "workshop/twin/params.json").readText()

    private fun tape(name: String) {
        val meta = TapeReplay.metas(dir).first { it["name"].toString().trim('"') == name }
        assertNull(TapeReplay.check(dir, meta, params))
    }

    @Test fun feedScroll() = tape("feed-scroll")

    @Test fun reels() = tape("reels")

    @Test fun video() = tape("video")

    @Test fun summary() {
        var ok = 0
        val metas = TapeReplay.metas(dir)
        for (m in metas) {
            val r = TapeReplay.check(dir, m, params)
            if (r == null) ok++ else println("MISMATCH $r")
        }
        println("TAPES $ok/${metas.size} exact")
        assertNull(if (ok == metas.size) null else "not all exact")
    }
}
