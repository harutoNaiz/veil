package com.veil.conductor.text

import java.io.DataInputStream
import java.io.File

/** Gemma-style byte-fallback BPE matching HF tokenizers (see VBPE pack in tokpack.py). */
class GemmaBpe(
    val prependMeta: Boolean,
    val splitMeta: Boolean,
    val bosId: Int,
    val eosId: Int,
    val unkId: Int,
    val padId: Int,
    private val vocab: Array<String>,
    private val merges: IntArray,
    private val added: List<Pair<String, Int>>
) {
    private val tokId =
        HashMap<String, Int>(vocab.size * 2).also { m ->
            for (i in vocab.indices) m[vocab[i]] = i
        }
    private val rank =
        HashMap<Long, Int>(merges.size).also { m ->
            for (r in 0 until merges.size / 3) {
                m[key(merges[r * 3], merges[r * 3 + 1])] = r
            }
        }
    private val addedSorted = added.sortedByDescending { it.first.length }

    fun encode(text: String): IntArray {
        val out = ArrayList<Int>()
        if (bosId >= 0) out.add(bosId)
        var seg = 0
        var i = 0
        while (i < text.length) {
            val hit = addedSorted.firstOrNull { text.startsWith(it.first, i) }
            if (hit != null) {
                encodeSegment(text.substring(seg, i), out)
                out.add(hit.second)
                i += hit.first.length
                seg = i
            } else {
                i++
            }
        }
        encodeSegment(text.substring(seg), out)
        if (eosId >= 0) out.add(eosId)
        return out.toIntArray()
    }

    private fun encodeSegment(raw: String, out: MutableList<Int>) {
        if (raw.isEmpty()) return
        var s = raw.replace(' ', META)
        if (prependMeta && s[0] != META) s = META + s
        if (!splitMeta) {
            bpe(s, out)
            return
        }
        var start = 0
        for (k in 1 until s.length) {
            if (s[k] == META) {
                bpe(s.substring(start, k), out)
                start = k
            }
        }
        bpe(s.substring(start), out)
    }

    private fun bpe(piece: String, out: MutableList<Int>) {
        val ids = ArrayList<Int>()
        var k = 0
        while (k < piece.length) {
            val str = String(Character.toChars(piece.codePointAt(k)))
            k += str.length
            val id = tokId[str]
            if (id != null) {
                ids.add(id)
                continue
            }
            val bids = str.toByteArray(Charsets.UTF_8).map { tokId[hex(it)] }
            if (bids.all { it != null }) {
                bids.forEach { ids.add(it!!) }
            } else if (ids.isEmpty() || ids.last() != unkId) {
                ids.add(unkId)
            }
        }
        while (ids.size > 1) {
            var best = Int.MAX_VALUE
            var at = -1
            for (j in 0 until ids.size - 1) {
                val r = rank[key(ids[j], ids[j + 1])]
                if (r != null && r < best) {
                    best = r
                    at = j
                }
            }
            if (at < 0) break
            ids[at] = merges[best * 3 + 2]
            ids.removeAt(at + 1)
        }
        out.addAll(ids)
    }

    companion object {
        private const val META = '▁'

        private fun key(l: Int, r: Int): Long = (l.toLong() shl 32) or (r.toLong() and 0xffffffffL)

        private fun hex(b: Byte): String = "<0x" + "%02X".format(b.toInt() and 0xff) + ">"

        fun load(f: File): GemmaBpe = DataInputStream(f.inputStream().buffered(1 shl 16)).use { d ->
            val magic = ByteArray(4).also { d.readFully(it) }
            require(String(magic, Charsets.US_ASCII) == "VBPE") { "bad magic" }
            require(d.readInt() == 1) { "bad version" }
            val prepend = d.readInt() != 0
            val split = d.readInt() != 0
            val bos = d.readInt()
            val eos = d.readInt()
            val unk = d.readInt()
            val pad = d.readInt()
            val vocab = Array(d.readInt()) { str(d) }
            val merges = IntArray(d.readInt() * 3) { d.readInt() }
            val added =
                List(d.readInt()) {
                    val id = d.readInt()
                    str(d) to id
                }
            GemmaBpe(prepend, split, bos, eos, unk, pad, vocab, merges, added)
        }

        private fun str(d: DataInputStream): String {
            val b = ByteArray(d.readUnsignedShort())
            d.readFully(b)
            return String(b, Charsets.UTF_8)
        }
    }
}
