package com.veil.guard.overlay.touch

data class Stroke(val path: List<Pair<Int, Int>>, val startMs: Long, val durationMs: Long)

object TouchReplay {
    const val TAP_MS = 50L

    /** Strokes to replay a Tap or Drag below a cover; LongPress is not replayed. */
    fun toStrokes(r: TouchResult): List<Stroke> = when (r) {
        is TouchResult.Tap -> listOf(Stroke(listOf(r.x to r.y), 0, TAP_MS))

        is TouchResult.Drag -> {
            val t0 = r.points.first().tMs
            val dur = (r.points.last().tMs - t0).coerceAtLeast(1)
            listOf(Stroke(r.points.map { it.x to it.y }, 0, dur))
        }

        is TouchResult.LongPress -> emptyList()
    }
}
