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

    /**
     * Screenshot of the foreground app window WITHOUT our overlay on top (takeScreenshotOfWindow, API 34+).
     * Implementations must only return it when the window covers the whole screen; otherwise fall back to
     * [takeScreenshot]. Default: the full-display screenshot.
     */
    fun takeAppWindowScreenshot(onResult: (android.hardware.HardwareBuffer?, errorCode: Int) -> Unit) =
        takeScreenshot(onResult)
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

/**
 * Own-cover coverage, so "no new frames" under our own opaque cover is not mistaken for a dead pipeline.
 * CaptureService installs the real probe; the default says "no cover".
 */
object OwnCoverBridge {
    /** Fraction 0..1 of the screen hidden by Veil's own covers right now. */
    @Volatile var coverage: () -> Double = { 0.0 }
}

/** Pure: union coverage of screen-px rects on a coarse grid (overlaps counted once). */
object CoverMath {
    private const val GX = 32
    private const val GY = 64

    fun fraction(rects: List<PxRect>, screenW: Int, screenH: Int): Double {
        if (rects.isEmpty() || screenW <= 0 || screenH <= 0) return 0.0
        val hit = BooleanArray(GX * GY)
        for (r in rects) {
            if (r.w <= 0 || r.h <= 0) continue
            val x0 = (r.x.toLong() * GX / screenW).toInt().coerceIn(0, GX)
            val x1 = (((r.x + r.w).toLong() * GX + screenW - 1) / screenW).toInt().coerceIn(0, GX)
            val y0 = (r.y.toLong() * GY / screenH).toInt().coerceIn(0, GY)
            val y1 = (((r.y + r.h).toLong() * GY + screenH - 1) / screenH).toInt().coerceIn(0, GY)
            for (y in y0 until y1) for (x in x0 until x1) hit[y * GX + x] = true
        }
        return hit.count { it }.toDouble() / hit.size
    }
}
