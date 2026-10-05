package com.veil.guard.wire

import com.veil.brain.contract.Record
import com.veil.conductor.DebugLog
import java.io.File

/** One JSON object per line. Plan lines carry both reader shapes (flat masks[].rect=[l,t,r,b] and nested plan). */
class JsonlDebugLog(private val sink: (String) -> Unit) : DebugLog {
    constructor(file: File) : this({ line ->
        file.parentFile?.mkdirs()
        file.appendText(line + "\n")
    })

    @Synchronized
    override fun write(rec: Record) {
        val out = if (rec["kind"] == "plan" || rec["kind"] == "maskPlan") planLine(rec) else rec
        runCatching { sink(encode(out)) }
    }

    private fun planLine(rec: Record): Record {
        val plan = (rec["plan"] as? Map<*, *>) ?: rec
        val masks =
            (plan["masks"] as? List<*>).orEmpty().mapNotNull { m ->
                val mm = m as? Map<*, *> ?: return@mapNotNull null
                val rect: List<Int> =
                    when (val r = mm["rect"]) {
                        is Map<*, *> -> {
                            val x = (r["x"] as Number).toInt()
                            val y = (r["y"] as Number).toInt()
                            listOf(x, y, x + (r["w"] as Number).toInt(), y + (r["h"] as Number).toInt())
                        }

                        is List<*> -> r.map { (it as Number).toInt() }

                        else -> return@mapNotNull null
                    }
                linkedMapOf("maskId" to mm["maskId"], "rect" to rect, "style" to mm["style"], "layer" to mm["layer"])
            }
        return linkedMapOf(
            "kind" to "plan",
            "tMs" to (rec["tMs"] ?: plan["tMs"]),
            "lookId" to rec["lookId"],
            "masks" to masks,
            "plan" to plan
        )
    }

    companion object {
        fun encode(v: Any?): String = StringBuilder().also { append(it, v) }.toString()

        private fun append(sb: StringBuilder, v: Any?) {
            when (v) {
                null -> sb.append("null")

                is Boolean -> sb.append(v)

                is Double -> sb.append(if (v.isFinite()) v.toString() else "null")

                is Float -> sb.append(if (v.isFinite()) v.toString() else "null")

                is Number -> sb.append(v.toString())

                is Map<*, *> -> {
                    sb.append('{')
                    var first = true
                    for ((k, x) in v) {
                        if (!first) sb.append(',')
                        first = false
                        str(sb, k.toString())
                        sb.append(':')
                        append(sb, x)
                    }
                    sb.append('}')
                }

                is Iterable<*> -> {
                    sb.append('[')
                    var first = true
                    for (x in v) {
                        if (!first) sb.append(',')
                        first = false
                        append(sb, x)
                    }
                    sb.append(']')
                }

                is IntArray -> append(sb, v.toList())

                is FloatArray -> append(sb, v.toList())

                else -> str(sb, v.toString())
            }
        }

        private fun str(sb: StringBuilder, s: String) {
            sb.append('"')
            for (c in s) {
                when {
                    c == '"' -> sb.append("\\\"")
                    c == '\\' -> sb.append("\\\\")
                    c == '\n' -> sb.append("\\n")
                    c == '\r' -> sb.append("\\r")
                    c == '\t' -> sb.append("\\t")
                    c < ' ' -> sb.append(String.format("\\u%04x", c.code))
                    else -> sb.append(c)
                }
            }
            sb.append('"')
        }
    }
}
