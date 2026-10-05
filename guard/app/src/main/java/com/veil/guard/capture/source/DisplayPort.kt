package com.veil.guard.capture.source

import com.veil.guard.capture.FrameSize

interface DisplayPort {
    fun create(size: FrameSize, dpi: Int)

    fun setSurfaceAttached(on: Boolean)

    fun resize(size: FrameSize, dpi: Int)
}
