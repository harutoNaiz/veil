package com.veil.teacher

import java.io.File
import java.util.Base64
import java.util.concurrent.atomic.AtomicInteger
import javax.crypto.AEADBadTagException
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test

class FakeEncoder : TextEncoder {
    override val spaceId = "siglip2-base-p16-224"
    override val textModelId = "siglip2-base-text"
    override fun encode(phrases: List<String>) = phrases.map { p ->
        FloatArray(8) { i -> ((p.hashCode() shr i) and 7) + 1f }
    }
}

class FixedKey(private val b: Byte) : KeyProvider {
    override fun key() = ByteArray(32) { b }
}

class TeacherTest {
    @Test fun cardMatchesPythonShape() {
        val c = Teacher.conceptCard("Cats")
        assertEquals("cats", c["conceptId"])
        assertEquals("Cats", c["displayName"])
        assertEquals("a photo of a cat", (c["looksLike"] as List<*>)[0])
        assertEquals(listOf("a dog", "a fox", "a lion", "a stuffed toy"), c["butNot"])
        assertEquals("grass", Teacher.singular("grass"))
        assertEquals(emptyList<String>(), Teacher.conceptCard("clowns")["butNot"])
    }

    @Test fun halfEncoding() {
        assertEquals(0x3c00, Teacher.doubleToHalf(1.0))
        assertEquals(0xbc00, Teacher.doubleToHalf(-1.0))
        assertEquals(0x3800, Teacher.doubleToHalf(0.5))
        assertEquals(0x0001, Teacher.doubleToHalf(Math.pow(2.0, -24.0)))
        assertEquals(0x3555, Teacher.doubleToHalf(1.0 / 3))
        val raw = Base64.getDecoder().decode(Teacher.encodeF16(floatArrayOf(3f, 4f)))
        assertEquals(4, raw.size)
    }

    @Test fun compileUsesCalibration() {
        val cc = Teacher.compile(Teacher.conceptCard("cats"), FakeEncoder())
        assertEquals(5, cc.looksLike.size)
        assertEquals(4, cc.butNot.size)
        assertEquals(3, cc.ignore.size)
        assertEquals(-0.477835, cc.calibrationOffset, 1e-12)
        assertEquals(0.35, cc.thresholds.getValue("balanced"), 1e-12)
        assertEquals(64, Teacher.conceptSha256(Teacher.conceptCard("cats")).length)
    }

    @Test fun storeRoundTripRestartAndWrongKey() {
        val f = File.createTempFile("veil", ".store").also {
            it.delete()
            it.deleteOnExit()
        }
        val doc = JsonObject(
            mapOf(
                "settings" to JsonObject(mapOf("mode" to JsonPrimitive("SECRETMARKER"))),
                "cards" to JsonArray(listOf(JsonPrimitive("cats"))),
                "corrections" to JsonArray(emptyList())
            )
        )
        SecureStore(f, FixedKey(1)).write(doc)
        assertEquals(doc, SecureStore(f, FixedKey(1)).read())
        assertFalse(String(f.readBytes(), Charsets.ISO_8859_1).contains("SECRETMARKER"))
        try {
            SecureStore(f, FixedKey(2)).read()
            fail("wrong key must throw")
        } catch (_: AEADBadTagException) {
            // expected
        }
    }

    @Test fun registrySwapNotifies() {
        val reg = ConceptRegistry()
        val n = AtomicInteger()
        reg.addListener { n.incrementAndGet() }
        val t0 = System.nanoTime()
        reg.put(Teacher.compile(Teacher.conceptCard("cats"), FakeEncoder()))
        assertTrue((System.nanoTime() - t0) < 1_000_000_000L)
        assertEquals(1, n.get())
        assertTrue(reg["cats"] != null)
        reg.remove("cats")
        assertEquals(2, n.get())
        assertTrue(reg.snapshot().isEmpty())
    }
}
