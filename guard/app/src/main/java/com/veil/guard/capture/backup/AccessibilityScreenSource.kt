package com.veil.guard.capture.backup

import android.graphics.Bitmap
import android.graphics.ColorSpace
import android.hardware.HardwareBuffer
import android.os.Handler
import android.os.HandlerThread
import android.os.SystemClock
import android.util.Log
import com.veil.guard.capture.CaptureGeometry
import com.veil.guard.capture.CapturedFrame
import com.veil.guard.capture.FrameSink
import com.veil.guard.capture.FrameSize
import com.veil.guard.capture.FrameSource
import com.veil.guard.capture.FrameSourceKind
import com.veil.guard.capture.PxRect
import com.veil.guard.capture.ScreenshotBridge
import com.veil.guard.capture.blind.BlindSpotDetector

/** Frame produced by the accessibility path: a downscaled bitmap owned by the frame until close(). */
private class BitmapFrame(
    override val frameId: Long,
    override val tMs: Long,
    override val size: FrameSize,
    override val screen: FrameSize,
    override val rotation: Int,
    override val blindRects: List<PxRect>,
    override val bitmap: Bitmap
) : CapturedFrame {
    override val source = FrameSourceKind.ACCESSIBILITY_SCREENSHOT
    override val hardwareBuffer: HardwareBuffer? = null

    override fun close() = bitmap.recycle()
}

/** Backup source: accessibility screenshots (~3 fps), downscaled, only when the picture changed. */
class AccessibilityScreenSource(
    private val bridge: ScreenshotBridge = ScreenshotBridge,
    private var screen: FrameSize,
    private var rotation: Int
) : FrameSource {
    override val kind = FrameSourceKind.ACCESSIBILITY_SCREENSHOT

    private val scheduler = ShotScheduler()
    private val dedupe = ThumbDedupe()
    private var thread: HandlerThread? = null
    private var handler: Handler? = null
    private var sink: FrameSink? = null
    private var frameId = 0L

    @Volatile private var running = false

    override fun start(sink: FrameSink) {
        if (bridge.provider == null) {
            Log.w(TAG, "Unavailable: no ScreenshotProvider (accessibility service not connected)")
            return
        }
        this.sink = sink
        running = true
        val t = HandlerThread("a11y-shots").also { it.start() }
        thread = t
        handler = Handler(t.looper).also { schedule(it) }
    }

    override fun pause() {
        scheduler.pause()
    }

    override fun resume() {
        scheduler.resume()
        handler?.let { schedule(it) }
    }

    override fun stop() {
        running = false
        handler?.removeCallbacksAndMessages(null)
        thread?.quitSafely()
        thread = null
        handler = null
        sink = null
    }

    override fun onRotation(screen: FrameSize, rotation: Int) {
        this.screen = screen
        this.rotation = rotation
        dedupe.reset()
    }

    private fun schedule(h: Handler) {
        h.removeCallbacksAndMessages(null)
        val delay = scheduler.delayUntilNext(SystemClock.uptimeMillis()) ?: return
        h.postDelayed({ shoot(h) }, delay)
    }

    private fun shoot(h: Handler) {
        val provider = bridge.provider
        if (!running || provider == null) return
        scheduler.onRequested(SystemClock.uptimeMillis())
        provider.takeScreenshot { buffer, error ->
            if (buffer != null) {
                try {
                    deliver(buffer)
                } finally {
                    buffer.close()
                }
            } else if (error == ERROR_INTERVAL_TOO_SHORT) {
                scheduler.onIntervalTooShort()
            } else {
                Log.w(TAG, "screenshot failed: $error")
            }
            if (running) schedule(h)
        }
    }

    private fun deliver(buffer: HardwareBuffer) {
        val target = CaptureGeometry.targetSize(screen)
        val hw = Bitmap.wrapHardwareBuffer(buffer, ColorSpace.get(ColorSpace.Named.SRGB)) ?: return
        val soft = hw.copy(Bitmap.Config.ARGB_8888, false)
        hw.recycle()
        val small = Bitmap.createScaledBitmap(soft, target.width, target.height, true)
        if (small !== soft) soft.recycle()
        val px = IntArray(target.width * target.height)
        small.getPixels(px, 0, target.width, 0, 0, target.width, target.height)
        val luma =
            ByteArray(px.size) { i ->
                val c = px[i]
                (((c shr 16 and 0xFF) * 77 + (c shr 8 and 0xFF) * 150 + (c and 0xFF) * 29) shr 8).toByte()
            }
        val out = sink
        if (out == null || !dedupe.changed(luma, target.width, target.height)) {
            small.recycle()
            return
        }
        val blind = BlindSpotDetector.detect(luma, target.width, target.height, emptyList())
        com.veil.guard.overlay.blind.BlindHintHub.onFrame(
            com.veil.guard.overlay.blind.BlindHintHub.isFullBlind(blind, target.width, target.height)
        )
        out.onFrame(
            BitmapFrame(
                frameId++,
                SystemClock.uptimeMillis(),
                target,
                screen,
                rotation,
                toScreen(blind, target),
                small
            )
        )
    }

    private fun toScreen(rects: List<PxRect>, target: FrameSize) = rects.map {
        PxRect(
            it.x * screen.width / target.width,
            it.y * screen.height / target.height,
            it.w * screen.width / target.width,
            it.h * screen.height / target.height
        )
    }

    private companion object {
        const val TAG = "A11yScreenSource"
        const val ERROR_INTERVAL_TOO_SHORT = 3
    }
}
