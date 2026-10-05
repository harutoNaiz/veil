package com.veil.guard.capture

enum class CaptureState(val wire: String) {
    RUNNING("running"),
    PAUSED("paused"),
    STOPPED("stopped"),
    AWAITING_PERMISSION("awaitingPermission")
}

enum class FrameSourceKind(val wire: String) {
    MEDIA_PROJECTION("mediaProjection"),
    ACCESSIBILITY_SCREENSHOT("accessibilityScreenshot")
}

data class PxRect(val x: Int, val y: Int, val w: Int, val h: Int)

data class FrameSize(val width: Int, val height: Int)

/** One delivered frame. The receiver MUST call close() as soon as it is done (guarantee to later phases). */
interface CapturedFrame : AutoCloseable {
    val frameId: Long
    val tMs: Long
    val size: FrameSize
    val screen: FrameSize
    val rotation: Int
    val source: FrameSourceKind
    val blindRects: List<PxRect>
    val hardwareBuffer: android.hardware.HardwareBuffer? // null in JVM tests / a11y path after downscale to bitmap
    val bitmap: android.graphics.Bitmap? // set on the a11y path
}

fun interface FrameSink {
    fun onFrame(frame: CapturedFrame)
}

interface FrameSource {
    val kind: FrameSourceKind

    fun start(sink: FrameSink)

    fun pause()

    fun resume()

    fun stop()

    fun onRotation(screen: FrameSize, rotation: Int)
}

/** Implemented by 4.2's accessibility service; full-resolution screenshot, callback on any thread. */
interface ScreenshotProvider {
    fun takeScreenshot(onResult: (android.hardware.HardwareBuffer?, errorCode: Int) -> Unit)
}

object ScreenshotBridge {
    @Volatile var provider: ScreenshotProvider? = null
}

/** Pure: shared by 4.1.2/4.1.3. Short side 360, long side rounded to even, aspect kept. */
object CaptureGeometry {
    fun targetSize(screen: FrameSize): FrameSize {
        val portrait = screen.height >= screen.width
        val s = minOf(screen.width, screen.height)
        val l = maxOf(screen.width, screen.height)
        val long = (Math.round(360.0 * l / s / 2.0) * 2).toInt()
        return if (portrait) FrameSize(360, long) else FrameSize(long, 360)
    }
}
