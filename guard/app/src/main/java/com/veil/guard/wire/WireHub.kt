package com.veil.guard.wire

import com.veil.brain.contract.UiEvent
import com.veil.conductor.DebugLog
import com.veil.conductor.Frame
import com.veil.conductor.LayoutNode
import com.veil.conductor.OverlayPort

/** Process-wide seams between W.1 (runtime), W.2 (pixels, models) and W.3 (signals, overlay). */
object WireHub {
    @Volatile var frames: ((Frame) -> Unit)? = null // W.1 sets; W.2 FrameAdapter calls (capture thread)

    @Volatile var events: ((UiEvent) -> Unit)? = null // W.1 sets; W.3 a11y service calls (main thread)

    @Volatile var drawn: ((Long) -> Unit)? = null // W.1 sets; W.3 LiveOverlay calls with uptime of first draw

    @Volatile var log: DebugLog? = null // W.1 sets; anyone writes {"kind":"warn",...}

    @Volatile var overlay: OverlayPort? = null // W.3 sets on a11y connect, null on unbind

    @Volatile var layout: () -> List<LayoutNode> = { emptyList() } // W.3 sets (LayoutFeed::latest)
}
