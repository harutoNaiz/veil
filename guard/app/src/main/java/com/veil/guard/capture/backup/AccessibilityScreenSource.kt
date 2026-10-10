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
import com.veil.guard.capture.OwnCoverBridge
import com.veil.guard.capture.PxRect
import com.veil.guard.capture.ScreenshotBridge
import com.veil.guard.capture.blind.BlindSpotDetector
import com.veil.guard.wire.WireHub

/** Frame produced by the accessibility path: a downscaled bitmap owned by the frame until close(). */
private class BitmapFrame(
    override val frameId: Long,
    override val tMs: Long,
    override val size: FrameSize,
    override val screen: FrameSize,
    override val rotation: Int,
    override val blindRects: List<PxRect>,
    override val bitmap: Bitmap,
    override val showsOwnCovers: Boolean = false
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

    // At most 3 shots/s in total (4-5/s overheated the phone); slower still on a still screen, see schedule().
    private val scheduler = DualShotScheduler(minGapMs = 333)
    private var pending: Runnable? = null
    private val dedupe = ThumbDedupe()

    // Display shots differ from window shots in the status bar and under our covers: compare like with like.
    private val dedupeDisplay = ThumbDedupe()
    private var thread: HandlerThread? = null
    private var handler: Handler? = null
    private var sink: FrameSink? = null
    private var frameId = 0L
    private var unchangedSince = 0L
    private var lastDeliveredMs = 0L
    private var unchangedLogged = false

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
        dedupeDisplay.reset()
    }

    /** Single pending runnable that re-evaluates which kind is due; callbacks of one kind never cancel the other. */
    private fun schedule(h: Handler) {
        pending?.let { h.removeCallbacks(it) }
        pending = null
        val now = SystemClock.uptimeMillis()
        val (kind, delay) = scheduler.next(now) ?: return
        // Nothing has changed for a second: about one shot per second until something moves (saves heat).
        val still = unchangedSince != 0L && now - unchangedSince >= STILL_AFTER_MS
        val r = Runnable { shoot(h, kind) }
        pending = r
        h.postDelayed(r, if (still) maxOf(delay, STILL_GAP_MS) else delay)
    }

    private fun shoot(h: Handler, kind: DualShotScheduler.Kind) {
        pending = null
        val provider = bridge.provider
        if (!running || provider == null) return
        scheduler.onRequested(kind, SystemClock.uptimeMillis())
        val onResult = { buffer: HardwareBuffer?, error: Int ->
            h.post {
                if (buffer != null) {
                    scheduler.onShot(kind)
                    try {
                        deliver(buffer, kind == DualShotScheduler.Kind.DISPLAY || error == DISPLAY_CONTENT)
                    } finally {
                        buffer.close()
                    }
                } else if (error == ERROR_INTERVAL_TOO_SHORT) {
                    scheduler.onTooShort(kind)
                } else {
                    Log.w(TAG, "screenshot failed: $error")
                }
                if (running) schedule(h)
            }
        }
        // Display shots include Veil's own overlay covers (window shots do not); acceptable for now.
        if (kind == DualShotScheduler.Kind.WINDOW) {
            provider.takeAppWindowScreenshot { b, e -> onResult(b, e) }
        } else {
            provider.takeScreenshot { b, e -> onResult(b, e) }
        }
        // The other kind may be due while this request is in flight.
        schedule(h)
    }

    private fun deliver(buffer: HardwareBuffer, ownCovers: Boolean) {
        // The shot itself has the current orientation (nothing reports rotations to this source): a landscape
        // full-screen video must not be squashed into the portrait size, or every cover lands in the wrong place.
        val shotScreen = if (buffer.width > 0 && buffer.height > 0) FrameSize(buffer.width, buffer.height) else screen
        screen = shotScreen
        val target = CaptureGeometry.targetSize(shotScreen)
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
        val now = SystemClock.uptimeMillis()
        val changed = (if (ownCovers) dedupeDisplay else dedupe).changed(luma, target.width, target.height)
        // Heartbeat: a still screen still sends a frame every HEARTBEAT_MS so the guard keeps checking it.
        if (out == null || (!changed && now - lastDeliveredMs < HEARTBEAT_MS)) {
            small.recycle()
            noteUnchanged()
            return
        }
        lastDeliveredMs = now
        unchangedSince = 0L
        unchangedLogged = false
        val blind = BlindSpotDetector.detect(luma, target.width, target.height, emptyList())
        com.veil.guard.overlay.blind.BlindHintHub.onFrame(
            com.veil.guard.overlay.blind.BlindHintHub.isFullBlind(blind, target.width, target.height)
        )
        out.onFrame(
            BitmapFrame(
                frameId++,
                SystemClock.uptimeMillis(),
                target,
                shotScreen,
                rotation,
                toScreen(blind, target),
                small,
                ownCovers
            )
        )
    }

    /** Unchanged screenshots are dropped by design (e.g. under our own opaque cover); say so once per episode. */
    private fun noteUnchanged() {
        val now = SystemClock.uptimeMillis()
        if (unchangedSince == 0L) unchangedSince = now
        if (!unchangedLogged && now - unchangedSince >= UNCHANGED_LOG_MS) {
            unchangedLogged = true
            WireHub.log?.write(
                linkedMapOf(
                    "kind" to "capture",
                    "tMs" to now,
                    "what" to "a11y-unchanged",
                    "detail" to "dropped as unchanged for ${now - unchangedSince}ms",
                    "cover" to OwnCoverBridge.coverage()
                )
            )
        }
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
        const val UNCHANGED_LOG_MS = 10_000L
        const val HEARTBEAT_MS = 800L
        const val STILL_AFTER_MS = 1000L
        const val STILL_GAP_MS = 900L
        const val ERROR_INTERVAL_TOO_SHORT = 3

        /** Code sent with a successful window request that fell back to a full-display shot. */
        const val DISPLAY_CONTENT = A11yDisplayFallback.CODE
    }
}
