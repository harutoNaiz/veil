package com.veil.guard.overlay.self

import com.veil.guard.overlay.OwnOverlayListener
import com.veil.guard.overlay.OwnOverlaySample
import com.veil.guard.overlay.Px
import java.io.File
import java.util.ArrayDeque

/** Rect history of our own drawn covers, looked up by capture time. */
class OwnOverlayRegistry(private val capacity: Int = 256, private val logFile: File? = null) : OwnOverlayListener {
    private val samples = ArrayDeque<OwnOverlaySample>()

    @Synchronized
    override fun onDrawn(sample: OwnOverlaySample) {
        if (samples.size >= capacity) samples.removeFirst()
        samples.addLast(sample)
        logFile?.let {
            val rects = sample.rects.joinToString(",") { r -> "{\"x\":${r.x},\"y\":${r.y},\"w\":${r.w},\"h\":${r.h}}" }
            it.appendText("{\"tMs\":${sample.tMs},\"rects\":[$rects]}\n")
        }
    }

    /** Latest sample with tMs <= [tMs]; empty if none. */
    @Synchronized
    fun at(tMs: Long): List<Px> = samples.lastOrNull { it.tMs <= tMs }?.rects ?: emptyList()

    companion object {
        /** Screen px to capture px, rounded outward. */
        fun scaled(rects: List<Px>, screenW: Int, screenH: Int, capW: Int, capH: Int): List<Px> = rects.map { r ->
            val x0 = Math.floor(r.x.toDouble() * capW / screenW).toInt()
            val y0 = Math.floor(r.y.toDouble() * capH / screenH).toInt()
            val x1 = Math.ceil((r.x + r.w).toDouble() * capW / screenW).toInt()
            val y1 = Math.ceil((r.y + r.h).toDouble() * capH / screenH).toInt()
            Px(x0, y0, x1 - x0, y1 - y0)
        }
    }
}
