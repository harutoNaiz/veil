package com.veil.conductor.text

import java.io.File
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class GemmaBpeTest {
    private fun check(pack: String, golden: String) {
        val f = File(pack)
        assertTrue("missing $pack", f.isFile)
        val bpe = GemmaBpe.load(f)
        val doc = Json.parseToJsonElement(File(golden).readText()) as JsonObject
        val strings = doc["strings"]!!.jsonArray
        val ids = doc["ids"]!!.jsonArray
        assertTrue(strings.size > 20)
        for (i in 0 until strings.size) {
            val s = strings[i].jsonPrimitive.content
            val want = (ids[i] as JsonArray).map { it.jsonPrimitive.int }.toIntArray()
            assertArrayEquals("case $i", want, bpe.encode(s))
        }
    }

    @Test
    fun toxicityGolden() = check(
        "../../data/forge/toxicity/toxicity-tok.bin",
        "src/test/resources/tok/golden-toxicity.json"
    )

    @Test
    fun siglip2Golden() = check(
        "../../data/forge/siglip2/siglip2-tok.bin",
        "src/test/resources/tok/golden-siglip2.json"
    )
}
