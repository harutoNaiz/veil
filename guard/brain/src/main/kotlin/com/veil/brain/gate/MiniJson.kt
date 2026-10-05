package com.veil.brain.gate

/** Tiny JSON reader (objects, arrays, strings, numbers, booleans, null) so :brain needs no dependencies. */
internal class MiniJson(private val s: String) {
    private var i = 0

    fun parse(): Any? {
        val v = value()
        ws()
        require(i == s.length) { "trailing JSON at $i" }
        return v
    }

    private fun ws() {
        while (i < s.length && s[i].isWhitespace()) i++
    }

    private fun value(): Any? {
        ws()
        return when (val c = s[i]) {
            '{' -> obj()
            '[' -> arr()
            '"' -> str()
            't' -> lit("true", true)
            'f' -> lit("false", false)
            'n' -> lit("null", null)
            else -> if (c == '-' || c.isDigit()) num() else error("bad JSON at $i")
        }
    }

    private fun lit(w: String, v: Any?): Any? {
        require(s.startsWith(w, i)) { "bad literal at $i" }
        i += w.length
        return v
    }

    private fun obj(): Map<String, Any?> {
        val m = LinkedHashMap<String, Any?>()
        i++
        ws()
        if (s[i] == '}') {
            i++
            return m
        }
        while (true) {
            ws()
            val k = str()
            ws()
            require(s[i++] == ':')
            m[k] = value()
            ws()
            val c = s[i++]
            if (c == '}') return m
            require(c == ',')
        }
    }

    private fun arr(): List<Any?> {
        val l = ArrayList<Any?>()
        i++
        ws()
        if (s[i] == ']') {
            i++
            return l
        }
        while (true) {
            l.add(value())
            ws()
            val c = s[i++]
            if (c == ']') return l
            require(c == ',')
        }
    }

    private fun str(): String {
        require(s[i] == '"')
        i++
        val sb = StringBuilder()
        while (s[i] != '"') {
            val c = s[i++]
            if (c == '\\') {
                when (val e = s[i++]) {
                    'n' -> sb.append('\n')

                    't' -> sb.append('\t')

                    'r' -> sb.append('\r')

                    'u' -> {
                        sb.append(s.substring(i, i + 4).toInt(16).toChar())
                        i += 4
                    }

                    else -> sb.append(e)
                }
            } else {
                sb.append(c)
            }
        }
        i++
        return sb.toString()
    }

    private fun num(): Any {
        val st = i
        while (i < s.length && (s[i].isDigit() || s[i] in "+-.eE")) i++
        val t = s.substring(st, i)
        return if (t.any { it in ".eE" }) t.toDouble() else t.toLong()
    }
}
