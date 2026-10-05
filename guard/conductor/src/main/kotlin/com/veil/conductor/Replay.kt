package com.veil.conductor

import com.veil.brain.contract.Record
import com.veil.brain.contract.UiEvent
import java.io.File

object Replay {
    /**
     * Interleaves by tMs (events, then findings, then the frame at equal tMs). findings are tape lines
     * {"tMs": delivery, "finding": {...}}; deliver defaults to injecting the finding straight into the brain.
     */
    fun run(
        c: Conductor,
        frames: Sequence<Frame>,
        events: List<UiEvent>,
        findings: List<Record>,
        out: File? = null,
        deliver: (Record) -> Unit = {
            @Suppress("UNCHECKED_CAST")
            c.inject(it["finding"] as Record)
        }
    ) {
        var ei = 0
        var fi = 0
        val w = out?.bufferedWriter()
        var last: Record? = null
        for (f in frames) {
            val t = f.meta.tMs
            while (ei < events.size && events[ei].tMs <= t) c.onEvent(events[ei++])
            while (fi < findings.size && (findings[fi]["tMs"] as Number).toLong() <= t) deliver(findings[fi++])
            c.offer(f)
            c.pump()
            val p = c.lastPlan
            if (w != null && p != null && p !== last) {
                w.write(toJson(p))
                w.newLine()
                last = p
            }
        }
        w?.close()
    }

    fun toJson(v: Any?): String = when (v) {
        null -> "null"
        is String -> "\"" + v.replace("\\", "\\\\").replace("\"", "\\\"") + "\""
        is Map<*, *> -> v.entries.joinToString(",", "{", "}") { toJson(it.key.toString()) + ":" + toJson(it.value) }
        is List<*> -> v.joinToString(",", "[", "]") { toJson(it) }
        else -> v.toString()
    }
}
