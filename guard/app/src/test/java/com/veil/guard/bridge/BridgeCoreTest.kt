package com.veil.guard.bridge

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.boolean
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class BridgeCoreTest {
    private class Fake : BridgeOps {
        val calls = ArrayList<String>()

        override fun state() = BridgeState(
            true,
            "strict",
            "running",
            mapOf("accessibility" to true),
            listOf("a.b"),
            listOf(BridgeConcept("c1", "Cats", true)),
            null
        )

        override fun start() {
            calls.add("start")
        }

        override fun pause() {
            calls.add("pause")
        }

        override fun resume() {
            calls.add("resume")
        }

        override fun stop() {
            calls.add("stop")
        }

        override fun setMode(mode: String) {
            calls.add("mode:$mode")
        }

        override fun setSkipList(packages: List<String>) {
            calls.add("skip:${packages.joinToString(",")}")
        }

        override fun installPack(json: String) {
            calls.add("pack")
        }

        override fun recentCovers(limit: Int) = listOf(BridgeCover("x", "c1", 5L))
    }

    private val ops = Fake()
    private val core = BridgeCore(ops)

    private fun call(s: String) = Json.parseToJsonElement(core.handle(s)).jsonObject

    @Test fun helloAndState() {
        assertEquals("1", call("""{"op":"hello"}""")["result"]!!.jsonObject["protocolVersion"]!!.jsonPrimitive.content)
        val st = call("""{"op":"getState"}""")["result"]!!.jsonObject
        assertEquals("strict", st["mode"]!!.jsonPrimitive.content)
        assertTrue(st["permissions"]!!.jsonObject["accessibility"]!!.jsonPrimitive.boolean)
        assertEquals("c1", st["concepts"]!!.jsonArray[0].jsonObject["conceptId"]!!.jsonPrimitive.content)
    }

    @Test fun commandsMapToOps() {
        for (r in listOf(
            """{"op":"start"}""",
            """{"op":"pause"}""",
            """{"op":"resume"}""",
            """{"op":"stop"}""",
            """{"op":"setMode","mode":"light"}""",
            """{"op":"setSkipList","packages":["p.q","r.s"]}"""
        )) {
            assertTrue(call(r)["ok"]!!.jsonPrimitive.boolean)
        }
        assertEquals(listOf("start", "pause", "resume", "stop", "mode:light", "skip:p.q,r.s"), ops.calls)
    }

    @Test fun badInputIsAnError() {
        assertFalse(call("""{"op":"setMode","mode":"loud"}""")["ok"]!!.jsonPrimitive.boolean)
        assertFalse(call("""{"op":"nope"}""")["ok"]!!.jsonPrimitive.boolean)
        assertFalse(call("not json")["ok"]!!.jsonPrimitive.boolean)
    }

    @Test fun packChecksum() {
        val json = """{"concepts":[]}"""
        val good = BridgeCore.sha256(json.toByteArray())
        val esc = json.replace("\"", "\\\"")
        assertEquals(
            "accepted",
            call("""{"op":"installPack","json":"$esc","sha256":"$good"}""")["result"]!!.jsonPrimitive.content
        )
        assertEquals(
            "rejectedChecksum",
            call("""{"op":"installPack","json":"$esc","sha256":"00"}""")["result"]!!.jsonPrimitive.content
        )
        val bad = "nope"
        val h = BridgeCore.sha256(bad.toByteArray())
        assertEquals(
            "rejectedInvalid",
            call("""{"op":"installPack","json":"$bad","sha256":"$h"}""")["result"]!!.jsonPrimitive.content
        )
        assertEquals(listOf("pack"), ops.calls)
    }

    @Test fun coversFromPlanLines() {
        val lines =
            listOf(
                """{"kind":"look","tMs":1}""",
                """{"kind":"plan","tMs":10,"masks":[{"maskId":"m1","layer":1},{"maskId":"m2","layer":2}]}""",
                "garbage"
            )
        val c = BridgeCore.coversFromLog(lines, 5)
        assertEquals(listOf("10-m1", "10-m2"), c.map { it.coverId })
        assertEquals(1, BridgeCore.coversFromLog(lines, 1).size)
    }
}
