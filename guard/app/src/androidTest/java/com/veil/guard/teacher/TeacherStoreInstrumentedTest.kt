package com.veil.guard.teacher

import androidx.test.platform.app.InstrumentationRegistry
import com.veil.teacher.ConceptRegistry
import com.veil.teacher.SecureStore
import com.veil.teacher.Teacher
import com.veil.teacher.TextEncoder
import java.io.File
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** Runs on the phone later (PHONE). Card time uses a stub encoder; the real-model time is measured by the debug screen. */
class TeacherStoreInstrumentedTest {
    private val ctx = InstrumentationRegistry.getInstrumentation().targetContext

    private val enc =
        object : TextEncoder {
            override val spaceId = "siglip2-base-p16-224"
            override val textModelId = "siglip2-base-text"

            override fun encode(phrases: List<String>) =
                phrases.map { p -> FloatArray(DIM) { (((p.hashCode() shr (it % BITS)) and 7) + 1).toFloat() } }
        }

    @Test
    fun cardUnderOneSecond() {
        val t0 = System.nanoTime()
        Teacher.compile(Teacher.conceptCard("spiders"), enc)
        assertTrue((System.nanoTime() - t0) < NS_PER_S)
    }

    @Test
    fun storeSurvivesNewInstance() {
        val f = File(ctx.filesDir, "test-store.bin")
        val doc = JsonObject(mapOf("settings" to JsonObject(mapOf("mode" to JsonPrimitive("strict")))))
        SecureStore(f, KeystoreKeyProvider(ctx)).write(doc)
        assertEquals(doc, SecureStore(f, KeystoreKeyProvider(ctx)).read())
    }

    @Test
    fun liveSwapUnderOneSecond() {
        val reg = ConceptRegistry()
        val t0 = System.nanoTime()
        reg.put(Teacher.compile(Teacher.conceptCard("cats"), enc))
        assertTrue((System.nanoTime() - t0) < NS_PER_S)
        assertTrue(reg["cats"] != null)
    }

    private companion object {
        const val DIM = 16
        const val BITS = 8
        const val NS_PER_S = 1_000_000_000L
    }
}
