package com.veil.brain.cache

class Sig(val thumb: ByteArray, val w: Int, val h: Int)

class FingerprintCache(val capacity: Int = 8000, val maxDist: Int = 10, val ttlMs: Long = 60000) {
    private class Entry(val fp: FloatArray, val t: Long, val sig: Sig?, val h: Long)

    private val e = LinkedHashMap<Int, Entry>()
    private var n = 0
    var hits = 0
        private set
    var misses = 0
        private set
    val size: Int get() = e.size

    private fun sigOk(a: Sig, b: Sig): Boolean {
        if (Math.abs(a.w - b.w) * 10 > a.w || Math.abs(a.h - b.h) * 10 > a.h) return false
        var sum = 0
        for (i in a.thumb.indices) sum += Math.abs((a.thumb[i].toInt() and 0xFF) - (b.thumb[i].toInt() and 0xFF))
        return sum / a.thumb.size <= SIG_MAD_MAX
    }

    fun get(h: Long, tMs: Long, sig: Sig? = null): FloatArray? {
        var bestD = 0
        var bestT = 0L
        var bestId = -1
        for ((id, en) in e) {
            if (tMs - en.t > ttlMs) continue
            val d = java.lang.Long.bitCount(h xor en.h)
            if (d > maxDist) continue
            if (sig != null && en.sig != null && !sigOk(sig, en.sig)) continue
            if (bestId == -1 || d < bestD || (d == bestD && en.t > bestT)) {
                bestD = d
                bestT = en.t
                bestId = id
            }
        }
        if (bestId == -1) {
            misses++
            return null
        }
        hits++
        val en = e.remove(bestId)!!
        e[bestId] = en
        return en.fp
    }

    fun put(h: Long, fingerprint: FloatArray, tMs: Long, sig: Sig? = null) {
        n++
        e[n] = Entry(fingerprint, tMs, sig, h)
        while (e.size > capacity) {
            val it = e.entries.iterator()
            it.next()
            it.remove()
        }
    }

    fun clear() = e.clear()

    companion object {
        const val SIG_MAD_MAX = 10
    }
}
