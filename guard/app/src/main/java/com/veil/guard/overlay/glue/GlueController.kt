package com.veil.guard.overlay.glue

import com.veil.guard.overlay.Cover
import com.veil.guard.overlay.CoverPlan
import com.veil.guard.overlay.CoverStyle
import com.veil.guard.overlay.OverlayCommands
import com.veil.guard.overlay.OverlayHub
import com.veil.guard.overlay.Px
import com.veil.guard.signals.RawEvent
import com.veil.guard.signals.ScrollTracker
import java.io.File

/** Wires scroll events to a [GluedBox] and submits it as a red cover. */
class GlueController(private val dir: File, private val screenW: Int, private val screenH: Int) {
    private val tracker = ScrollTracker()
    private var box: GluedBox? = null
    private var planId = 9000L

    fun register() {
        OverlayCommands.handlers["glue"] = { v -> command(v) }
    }

    fun command(value: String?) {
        when {
            value == "on" -> place(screenW / 2, screenH / 2)

            value == "off" -> {
                box = null
                OverlayHub.sink?.submit(plan(emptyList()))
            }

            value != null && value.startsWith("place:") -> {
                val p = value.removePrefix("place:").split(",")
                place(p[0].trim().toInt(), p[1].trim().toInt())
            }
        }
    }

    private fun place(cx: Int, cy: Int) {
        tracker.reset()
        box = GluedBox(Px(cx - BOX / 2, cy - BOX / 2, BOX, BOX)).also { submit(it) }
    }

    /** Called by the host for every raw scroll event. */
    fun onEvent(raw: RawEvent) {
        val b = box ?: return
        val d = tracker.onScroll(raw) ?: return
        if (b.apply(d, raw.tMs)) {
            submit(b)
            val p = b.position()
            val line = "{\"tMs\":${raw.tMs},\"x\":${p.x},\"y\":${p.y},\"eventDy\":${d.dy},\"eventDx\":${d.dx}}\n"
            runCatching {
                dir.mkdirs()
                File(dir, "glue.jsonl").appendText(line)
            }
        }
    }

    private fun submit(b: GluedBox) {
        val cover = Cover(9001, b.position(), CoverStyle.SOLID, 0, false, "glue")
        OverlayHub.sink?.submit(plan(listOf(cover)))
    }

    private fun plan(covers: List<Cover>) =
        CoverPlan(++planId, System.currentTimeMillis(), screenW, screenH, 0, covers, "glue")

    private companion object {
        const val BOX = 200
    }
}
