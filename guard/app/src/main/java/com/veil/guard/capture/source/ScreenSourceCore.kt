package com.veil.guard.capture.source

import com.veil.guard.capture.CaptureGeometry
import com.veil.guard.capture.FrameSize

/**
 * Pure driver: the display is created exactly once; pause/resume only detach/attach; rotation resizes.
 * [onState] reports every state change ("created", "attached", "detached", "resized", "reattached",
 * "reader-recreated") for the debug log.
 */
class ScreenSourceCore(
    private val port: DisplayPort,
    private var screen: FrameSize,
    private val dpi: Int,
    private val onState: (String) -> Unit = {}
) {
    private var created = false
    var attached = false
        private set

    fun start() {
        check(!created) { "display already created" }
        created = true
        port.create(CaptureGeometry.targetSize(screen), dpi)
        onState("created")
        attached = true
        port.setSurfaceAttached(true)
        onState("attached")
    }

    fun pause() {
        if (!created || !attached) return
        attached = false
        port.setSurfaceAttached(false)
        onState("detached")
    }

    fun resume() {
        if (!created || attached) return
        attached = true
        port.setSurfaceAttached(true)
        onState("attached")
    }

    fun rotate(newScreen: FrameSize) {
        screen = newScreen
        if (created) {
            port.resize(CaptureGeometry.targetSize(newScreen), dpi)
            onState("resized")
        }
    }

    /** Watchdog recovery: detach then re-attach the same surface. No-op while paused. */
    fun reattach(): Boolean {
        if (!created || !attached) return false
        port.setSurfaceAttached(false)
        port.setSurfaceAttached(true)
        onState("reattached")
        return true
    }

    /** Watchdog recovery: dpi flip on the existing display. No-op while paused. */
    fun nudge(): Boolean {
        if (!created || !attached) return false
        port.nudge()
        onState("nudged")
        return true
    }

    /** Watchdog recovery: new ImageReader on the existing display. No-op while paused. */
    fun recreateReader(): Boolean {
        if (!created || !attached) return false
        port.recreateReader()
        onState("reader-recreated")
        return true
    }
}
