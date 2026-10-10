package com.veil.guard.capture.source

import com.veil.guard.capture.FrameSize

interface DisplayPort {
    fun create(size: FrameSize, dpi: Int)

    fun setSurfaceAttached(on: Boolean)

    fun resize(size: FrameSize, dpi: Int)

    /** Flip dpi and back to make the system re-configure the content recording. */
    fun nudge()

    /** Replace the ImageReader (same size) and point the existing display at it. */
    fun recreateReader()
}
