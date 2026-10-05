package com.veil.guard.capture.source

import com.veil.guard.capture.CaptureGeometry
import com.veil.guard.capture.FrameSize

/** Pure driver: the display is created exactly once; pause/resume only detach/attach; rotation resizes. */
class ScreenSourceCore(private val port: DisplayPort, private var screen: FrameSize, private val dpi: Int) {
    private var created = false
    var attached = false
        private set

    fun start() {
        check(!created) { "display already created" }
        created = true
        port.create(CaptureGeometry.targetSize(screen), dpi)
        attached = true
        port.setSurfaceAttached(true)
    }

    fun pause() {
        if (!created || !attached) return
        attached = false
        port.setSurfaceAttached(false)
    }

    fun resume() {
        if (!created || attached) return
        attached = true
        port.setSurfaceAttached(true)
    }

    fun rotate(newScreen: FrameSize) {
        screen = newScreen
        if (created) port.resize(CaptureGeometry.targetSize(newScreen), dpi)
    }
}
