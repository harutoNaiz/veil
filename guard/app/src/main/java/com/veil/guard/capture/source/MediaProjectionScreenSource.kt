package com.veil.guard.capture.source

import android.graphics.Bitmap
import android.graphics.PixelFormat
import android.hardware.HardwareBuffer
import android.hardware.display.DisplayManager
import android.hardware.display.VirtualDisplay
import android.media.Image
import android.media.ImageReader
import android.media.projection.MediaProjection
import android.os.Handler
import android.os.HandlerThread
import android.os.SystemClock
import com.veil.guard.capture.CapturedFrame
import com.veil.guard.capture.FrameSink
import com.veil.guard.capture.FrameSize
import com.veil.guard.capture.FrameSource
import com.veil.guard.capture.FrameSourceKind
import com.veil.guard.capture.PxRect
import com.veil.guard.wire.WireHub
import java.util.concurrent.atomic.AtomicLong

class MediaProjectionScreenSource(
    private val projection: MediaProjection,
    screen: FrameSize,
    private val dpi: Int,
    private var rotation: Int,
    private val isScreenOn: () -> Boolean = { true },
    private val onDead: (String) -> Unit = {},
    private val coverage: () -> Double = { 0.0 }
) : FrameSource {
    override val kind = FrameSourceKind.MEDIA_PROJECTION
    val gate = FrameGate()
    val meter = FrameRateMeter()

    private var screenSize = screen
    private var sink: FrameSink? = null
    private var thread: HandlerThread? = null
    private var handler: Handler? = null
    private var wdThread: HandlerThread? = null
    private var wdHandler: Handler? = null
    private var reader: ImageReader? = null
    private var readerSize: FrameSize? = null
    private var display: VirtualDisplay? = null
    private val ids = AtomicLong(0)
    private val lock = Any()
    private val core = ScreenSourceCore(Port(), screen, dpi) { dlog("state", it) }
    private val watchdog = FrameWatchdog()

    @Volatile private var framesSeen = 0L

    @Volatile private var lastPingMs = 0L

    @Volatile private var running = false
    private var lastBlockedLogMs = 0L
    private var coverHeld = false

    override fun start(sink: FrameSink) {
        this.sink = sink
        val t = HandlerThread("veil-capture").also { it.start() }
        thread = t
        handler = Handler(t.looper)
        val now = SystemClock.elapsedRealtime()
        lastPingMs = now
        synchronized(watchdog) { watchdog.arm(now) }
        running = true
        synchronized(lock) { core.start() }
        val w = HandlerThread("veil-capture-wd").also { it.start() }
        wdThread = w
        wdHandler = Handler(w.looper).also { it.postDelayed(tick, TICK_MS) }
    }

    override fun pause() {
        synchronized(lock) { core.pause() }
    }

    override fun resume() {
        synchronized(lock) { core.resume() }
        synchronized(watchdog) { watchdog.arm(SystemClock.elapsedRealtime()) }
    }

    override fun onRotation(screen: FrameSize, rotation: Int) {
        this.rotation = rotation
        screenSize = screen
        synchronized(lock) { core.rotate(screen) }
    }

    /** Elapsed ms since the last frame reached the sink (or since start). */
    fun sinceLastFrameMs(): Long = synchronized(watchdog) { watchdog.silentMs(SystemClock.elapsedRealtime()) }

    /** One-line VirtualDisplay/reader state for the debug log. */
    fun describe(): String = synchronized(lock) {
        val d = display?.display
        "vd=${if (display == null) "null" else "ok"} state=${d?.state} id=${d?.displayId} " +
            "valid=${d?.isValid} reader=${readerSize?.width}x${readerSize?.height} attached=${core.attached} " +
            "frames=$framesSeen screenOn=${isScreenOn()}"
    }

    /** Manual recovery hook for `cmd mprecover` (reattach|nudge|recreate|dump). */
    fun recover(what: String) {
        dlog("manual-recover", what, mapOf("display" to describe(), "sinceFrameMs" to sinceLastFrameMs()))
        synchronized(lock) {
            when (what) {
                "reattach" -> core.reattach()
                "nudge" -> core.nudge()
                "recreate" -> core.recreateReader()
                else -> false
            }
        }
    }

    override fun stop() {
        running = false
        dlog("state", "stopping")
        sink = null
        wdHandler?.removeCallbacksAndMessages(null)
        wdThread?.quitSafely()
        wdThread = null
        synchronized(lock) {
            display?.release()
            display = null
            reader?.close()
            reader = null
        }
        thread?.quitSafely()
        thread = null
    }

    private fun dlog(what: String, detail: String, extra: Map<String, Any?> = emptyMap()) {
        val rec = linkedMapOf<String, Any?>("kind" to "capture", "tMs" to SystemClock.uptimeMillis())
        rec["what"] = what
        rec["detail"] = detail
        rec.putAll(extra)
        WireHub.log?.write(rec)
    }

    private fun dwarn(what: String, extra: Map<String, Any?> = emptyMap()) {
        val rec = linkedMapOf<String, Any?>("kind" to "warn", "tMs" to SystemClock.uptimeMillis())
        rec["what"] = what
        rec.putAll(extra)
        WireHub.log?.write(rec)
    }

    private fun newReader(size: FrameSize): ImageReader {
        val r = ImageReader.newInstance(
            size.width,
            size.height,
            PixelFormat.RGBA_8888,
            3,
            HardwareBuffer.USAGE_GPU_SAMPLED_IMAGE or HardwareBuffer.USAGE_CPU_READ_RARELY
        )
        r.setOnImageAvailableListener({ onAvailable(it, size) }, handler)
        return r
    }

    private fun onAvailable(r: ImageReader, size: FrameSize) {
        try {
            val image = r.acquireLatestImage() ?: return
            val s = sink
            val now = SystemClock.elapsedRealtime()
            if (s == null || !gate.tryAcquire(now)) {
                image.close()
                return
            }
            framesSeen++
            meter.record(now)
            val pending = synchronized(watchdog) { watchdog.onFrame(now) }
            if (pending != FrameWatchdog.Action.NONE) {
                dlog("recovered", "frame after ${pending.name}", mapOf("frames" to framesSeen))
            }
            if (framesSeen == 1L || framesSeen % 200 == 0L) {
                dlog("frame", "n=$framesSeen", mapOf("dropped" to gate.dropped))
            }
            val frame = ImageFrame(image, ids.incrementAndGet(), now, size, screenSize, rotation, gate.epoch)
            try {
                s.onFrame(frame)
            } catch (t: Throwable) {
                frame.close()
                dwarn("capture-sink-error", mapOf("why" to t.toString()))
            }
        } catch (t: Throwable) {
            // IllegalStateException from a closed/starved reader must not kill the capture thread
            dwarn("capture-acquire-error", mapOf("why" to t.toString()))
        }
    }

    private val tick: Runnable =
        object : Runnable {
            override fun run() {
                if (!running) return
                try {
                    watchdogTick()
                } catch (t: Throwable) {
                    dwarn("capture-watchdog-error", mapOf("why" to t.toString()))
                }
                if (running) wdHandler?.postDelayed(this, TICK_MS)
            }
        }

    private fun watchdogTick() {
        val now = SystemClock.elapsedRealtime()
        val h = handler
        // capture-thread liveness: a stale ping means the looper is blocked (synchronous consumer?)
        h?.post { lastPingMs = SystemClock.elapsedRealtime() }
        if (now - lastPingMs > BLOCKED_MS && now - lastBlockedLogMs > BLOCKED_MS) {
            lastBlockedLogMs = now
            val stack = thread?.stackTrace?.take(14)?.joinToString(" | ") { it.toString() }
            dwarn("capture-thread-blocked", mapOf("ms" to now - lastPingMs, "stack" to stack))
        }
        // gate stuck: a lease nobody released would silently drop every frame
        val held = gate.heldMs(now)
        if (held > GATE_STUCK_MS) {
            val n = gate.forceReset()
            dwarn("capture-gate-stuck", mapOf("heldMs" to held, "outstanding" to n))
        }
        val screenOn = isScreenOn()
        val attached = synchronized(lock) { core.attached }
        // under our own opaque cover the mirrored picture is legitimately static: hold the silence clock
        val cover = coverage()
        val underCover = cover >= COVER_HOLD
        if (underCover != coverHeld) {
            coverHeld = underCover
            dlog("cover-hold", underCover.toString(), mapOf("cover" to cover, "sinceFrameMs" to sinceLastFrameMs()))
        }
        val action = synchronized(watchdog) { watchdog.check(now, screenOn && attached && !underCover) }
        if (action == FrameWatchdog.Action.NONE) return
        val info =
            mapOf(
                "silentMs" to synchronized(watchdog) { watchdog.silentMs(now) },
                "frames" to framesSeen,
                "outstanding" to gate.outstanding,
                "dropped" to gate.dropped,
                "screenOn" to screenOn,
                "attached" to attached,
                "display" to describe(),
                "cover" to cover
            )
        // a static screen legitimately yields no frames; this is a warning, recovery is cheap
        dwarn("capture-stalled-${action.name.lowercase()}", info)
        when (action) {
            FrameWatchdog.Action.POLL ->
                h?.post {
                    val r = reader
                    val size = readerSize
                    if (r != null && size != null) onAvailable(r, size)
                }

            FrameWatchdog.Action.REATTACH -> synchronized(lock) { core.reattach() }

            FrameWatchdog.Action.NUDGE -> synchronized(lock) { core.nudge() }

            FrameWatchdog.Action.RECREATE -> synchronized(lock) { core.recreateReader() }

            FrameWatchdog.Action.GIVEUP -> {
                dwarn("capture-dead", mapOf("display" to describe()))
                onDead("no frames after reattach/nudge/recreate")
            }

            FrameWatchdog.Action.NONE -> Unit
        }
    }

    private inner class ImageFrame(
        private val image: Image,
        override val frameId: Long,
        override val tMs: Long,
        override val size: FrameSize,
        override val screen: FrameSize,
        override val rotation: Int,
        private val gateEpoch: Int
    ) : CapturedFrame {
        private var closed = false
        private val handedOut = mutableListOf<HardwareBuffer>()
        override val source = FrameSourceKind.MEDIA_PROJECTION
        override val blindRects: List<PxRect> = emptyList()

        // Image.getHardwareBuffer() returns a NEW HardwareBuffer reference per call; all are closed in close().
        override val hardwareBuffer: HardwareBuffer?
            @Synchronized get() = if (closed) null else image.hardwareBuffer?.also { handedOut += it }
        override val bitmap: Bitmap? = null

        @Synchronized
        override fun close() {
            if (closed) return
            closed = true
            handedOut.forEach { runCatching { it.close() } }
            handedOut.clear()
            try {
                image.close()
            } finally {
                gate.release(gateEpoch)
            }
        }
    }

    private inner class Port : DisplayPort {
        override fun create(size: FrameSize, dpi: Int) {
            val r = newReader(size)
            reader = r
            readerSize = size
            display = projection.createVirtualDisplay(
                "veil-capture",
                size.width,
                size.height,
                dpi,
                DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
                r.surface,
                null,
                null
            )
        }

        override fun setSurfaceAttached(on: Boolean) {
            display?.setSurface(if (on) reader?.surface else null)
        }

        override fun resize(size: FrameSize, dpi: Int) {
            val old = reader
            val r = newReader(size)
            reader = r
            readerSize = size
            display?.resize(size.width, size.height, dpi)
            display?.setSurface(r.surface)
            old?.close()
        }

        override fun nudge() {
            val size = readerSize ?: return
            display?.resize(size.width, size.height, dpi + 1)
            display?.resize(size.width, size.height, dpi)
        }

        override fun recreateReader() {
            val size = readerSize ?: return
            val old = reader
            val r = newReader(size)
            reader = r
            display?.setSurface(r.surface)
            old?.close()
        }
    }

    private companion object {
        const val TICK_MS = 1_000L
        const val COVER_HOLD = 0.6
        const val BLOCKED_MS = 4_000L
        const val GATE_STUCK_MS = 5_000L
    }
}
