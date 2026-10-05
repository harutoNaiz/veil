package com.veil.guard.overlay

import java.io.File

/** Appends render.jsonl and own.jsonl lines under files/overlay/. */
class RenderTrace(private val dir: File) {
    @Synchronized
    fun render(planId: Long, tRecvMs: Long, tDrawnMs: Long, vsyncPeriodMs: Double, covers: Int) = append(
        "render.jsonl",
        "{\"planId\":$planId,\"tRecvMs\":$tRecvMs,\"tDrawnMs\":$tDrawnMs," +
            "\"vsyncPeriodMs\":$vsyncPeriodMs,\"covers\":$covers}"
    )

    @Synchronized
    fun own(s: OwnOverlaySample) {
        val rects = s.rects.joinToString(",") { "{\"x\":${it.x},\"y\":${it.y},\"w\":${it.w},\"h\":${it.h}}" }
        append("own.jsonl", "{\"tMs\":${s.tMs},\"rects\":[$rects]}")
    }

    private fun append(name: String, line: String) {
        dir.mkdirs()
        File(dir, name).appendText(line + "\n")
    }
}
