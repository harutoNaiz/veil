package com.veil.teacher.autocal

import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.security.MessageDigest

/** Reads a bank.bin ("VBNK" v1, little-endian). */
class BankFile(bytes: ByteArray) {
    val n: Int
    val dim: Int
    val scale: FloatArray
    val q: ByteArray
    val labOff: IntArray
    val labIdx: IntArray
    val bankId: String = MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02x".format(it) }
        .take(ID_LEN)

    /** 1 / |q row|: dequantised rows are l2(q*scale), so the scale cancels. */
    val invNorm: DoubleArray

    init {
        val b = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
        require(b.int == MAGIC) { "not a VBNK file" }
        require(b.int == 1) { "bank version" }
        n = b.int
        dim = b.int
        val nLab = b.int
        scale = FloatArray(n) { b.float }
        q = ByteArray(n * dim)
        b.get(q)
        labOff = IntArray(n + 1) { b.int }
        labIdx = IntArray(nLab) { b.short.toInt() and 0xFFFF }
        invNorm = DoubleArray(n) { r ->
            var s = 0.0
            for (i in 0 until dim) {
                val x = q[r * dim + i].toDouble()
                s += x * x
            }
            if (s > 0) 1.0 / Math.sqrt(s) else 0.0
        }
    }

    /** True for rows whose labels hit [excl]. */
    fun excludedMask(excl: Set<Int>): BooleanArray = BooleanArray(n) { r ->
        (labOff[r] until labOff[r + 1]).any { labIdx[it] in excl }
    }

    /** Float64 dots of a unit vector against every dequantised row. */
    fun scores(e: DoubleArray): DoubleArray = DoubleArray(n) { r ->
        var s = 0.0
        val o = r * dim
        for (i in 0 until dim) s += q[o + i] * e[i]
        s * invNorm[r]
    }

    companion object {
        private const val MAGIC = 0x4B4E4256 // "VBNK" little-endian
        private const val ID_LEN = 16

        fun load(f: File) = BankFile(f.readBytes())
    }
}
