package com.veil.teacher

import com.veil.brain.learn.CorrectionBook
import com.veil.brain.learn.Feedback
import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class CorrectionStoreTest {
    private class Key(private val b: Byte) : KeyProvider {
        override fun key() = ByteArray(32) { b }
    }

    private fun file() = File.createTempFile("corr", ".bin").also { it.delete() }

    @Test
    fun roundTripEncrypted() {
        val f = file()
        val book = CorrectionBook()
        book.record(Feedback("notThis", "cat"), DoubleArray(8) { it + 1.0 })
        book.record(Feedback("notThis", "cat"), null)
        CorrectionStore(SecureStore(f, Key(1))).save(book)
        assertFalse(String(f.readBytes(), Charsets.ISO_8859_1).contains("nudge"))
        val back = CorrectionStore(SecureStore(f, Key(1))).load()
        assertEquals(0.04, back.nudgeOf("cat"), 1e-9)
        assertEquals(1, back.exceptionCount("cat"))
    }

    @Test
    fun wrongKeyFails() {
        val f = file()
        CorrectionStore(SecureStore(f, Key(1))).save(CorrectionBook())
        assertTrue(runCatching { CorrectionStore(SecureStore(f, Key(2))).load() }.isFailure)
    }
}
