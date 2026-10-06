package com.veil.guard.wire.ml

import com.veil.conductor.text.GemmaBpe
import java.io.File
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class Siglip2TokenizerTest {
    @Test
    fun goldenMatchesTwinForEveryTemplate() {
        val pack = File("../../data/forge/siglip2/siglip2-tok.bin")
        assertTrue("missing $pack", pack.isFile)
        val tok = Siglip2Tokenizer(GemmaBpe.load(pack))
        val doc = Json.parseToJsonElement(File("src/test/resources/tok/golden-oov.json").readText()) as JsonObject
        val strings = doc["strings"]!!.jsonArray
        val ids = doc["ids"]!!.jsonArray
        assertEquals(15, strings.size)
        for (i in 0 until strings.size) {
            val want = ids[i].jsonArray.map { it.jsonPrimitive.int.toLong() }.toLongArray()
            assertEquals(64, want.size)
            assertArrayEquals("case $i", want, tok.ids(strings[i].jsonPrimitive.content))
        }
    }
}
