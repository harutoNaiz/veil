package com.veil.runtime

object ProfileCheck {
    private val node = Regex("\"cat\"\\s*:\\s*\"Node\"")
    private val provider = Regex("\"provider\"\\s*:\\s*\"([^\"]*)\"")

    fun providerCounts(ortProfileJson: String): Map<String, Int> {
        val counts = LinkedHashMap<String, Int>()
        val starts = node.findAll(ortProfileJson).map { it.range.first }.toList()
        for ((i, st) in starts.withIndex()) {
            val end = if (i + 1 < starts.size) starts[i + 1] else ortProfileJson.length
            val p = provider.find(ortProfileJson.substring(st, end))?.groupValues?.get(1) ?: continue
            counts[p] = (counts[p] ?: 0) + 1
        }
        return counts
    }

    fun allOnNpu(json: String): Boolean {
        val c = providerCounts(json)
        return c.isNotEmpty() && c.keys.all { it == "QNNExecutionProvider" }
    }
}
