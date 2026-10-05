package com.veil.guard.capture.state

import com.veil.guard.capture.FrameSize
import kotlin.math.abs

/** Pure: is the captured content effectively the whole display (within relative tolerance)? */
object EntireScreenCheck {
    fun isEntireScreen(content: FrameSize, display: FrameSize, tol: Double = 0.02): Boolean {
        if (display.width <= 0 || display.height <= 0) return false
        val wDelta = abs(content.width - display.width).toDouble() / display.width
        val hDelta = abs(content.height - display.height).toDouble() / display.height
        return wDelta <= tol && hDelta <= tol
    }
}
