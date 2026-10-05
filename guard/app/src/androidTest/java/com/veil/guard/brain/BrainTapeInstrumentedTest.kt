package com.veil.guard.brain

import androidx.test.platform.app.InstrumentationRegistry
import com.veil.brain.contract.FrameMeta
import com.veil.brain.contract.Rect
import com.veil.brain.contract.UiEvent
import com.veil.brain.motion.BrainPipeline
import java.util.Base64
import org.junit.Assert.assertTrue
import org.junit.Test

/** Replays the golden tapes (androidTest assets) and checks the record counts per tape. Runs on the phone later. */
class BrainTapeInstrumentedTest {
    private val assets = InstrumentationRegistry.getInstrumentation().context.assets

    private fun str(line: String, key: String) = Regex("\"$key\":\"([^\"]*)\"").find(line)?.groupValues?.get(1)

    private fun lng(line: String, key: String) =
        Regex("\"$key\":(-?\\d+)").find(line)?.groupValues?.get(1)?.toLong() ?: 0L

    @Test
    fun tapesReplay() {
        val params = assets.open("params.json").bufferedReader().readText()
        for (name in listOf("feed-scroll", "reels", "video")) {
            val pipe = BrainPipeline("balanced", params)
            var w = 0
            var h = 0
            var sw = 0
            var sh = 0
            var records = 0
            assets.open("$name.tape-in.jsonl").bufferedReader().forEachLine { line ->
                when (str(line, "kind")) {
                    "header" -> {
                        w = lng(line, "width").toInt()
                        h = lng(line, "height").toInt()
                        sw = lng(line, "screenWidth").toInt()
                        sh = lng(line, "screenHeight").toInt()
                    }

                    "event" ->
                        pipe.onEvent(
                            UiEvent(
                                str(line, "type") ?: "",
                                lng(line, "tMs"),
                                dy = lng(line, "dy").toInt(),
                                packageName = str(line, "packageName")
                            )
                        )

                    "frame" -> {
                        val fm =
                            FrameMeta(lng(line, "frameId").toInt(), lng(line, "tMs"), w, h, sw, sh, emptyList<Rect>())
                        records += pipe.step(Base64.getDecoder().decode(str(line, "thumb")), fm).size
                    }
                }
            }
            assertTrue("tape $name produced no records", records > 0)
        }
    }
}
