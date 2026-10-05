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
import java.util.concurrent.atomic.AtomicLong

class MediaProjectionScreenSource(
    private val projection: MediaProjection,
    screen: FrameSize,
    private val dpi: Int,
    private var rotation: Int
) : FrameSource {
    override val kind = FrameSourceKind.MEDIA_PROJECTION
    val gate = FrameGate()
    val meter = FrameRateMeter()

    private var screenSize = screen
    private var sink: FrameSink? = null
    private var thread: HandlerThread? = null
    private var handler: Handler? = null
    private var reader: ImageReader? = null
    private var display: VirtualDisplay? = null
    private val ids = AtomicLong(0)
    private val core = ScreenSourceCore(Port(), screen, dpi)

    override fun start(sink: FrameSink) {
        this.sink = sink
        val t = HandlerThread("veil-capture").also { it.start() }
        thread = t
        handler = Handler(t.looper)
        core.start()
    }

    override fun pause() = core.pause()

    override fun resume() = core.resume()

    override fun onRotation(screen: FrameSize, rotation: Int) {
        this.rotation = rotation
        screenSize = screen
        core.rotate(screen)
    }

    override fun stop() {
        sink = null
        display?.release()
        display = null
        reader?.close()
        reader = null
        thread?.quitSafely()
        thread = null
    }

    private fun newReader(size: FrameSize): ImageReader {
        val r = ImageReader.newInstance(
            size.width,
            size.height,
            PixelFormat.RGBA_8888,
            2,
            HardwareBuffer.USAGE_GPU_SAMPLED_IMAGE or HardwareBuffer.USAGE_CPU_READ_RARELY
        )
        r.setOnImageAvailableListener({ onAvailable(it, size) }, handler)
        return r
    }

    private fun onAvailable(r: ImageReader, size: FrameSize) {
        val image = r.acquireLatestImage() ?: return
        val s = sink
        if (s == null || !gate.tryAcquire()) {
            image.close()
            return
        }
        val now = SystemClock.elapsedRealtime()
        meter.record(now)
        s.onFrame(ImageFrame(image, ids.incrementAndGet(), now, size, screenSize, rotation))
    }

    private inner class ImageFrame(
        private val image: Image,
        override val frameId: Long,
        override val tMs: Long,
        override val size: FrameSize,
        override val screen: FrameSize,
        override val rotation: Int
    ) : CapturedFrame {
        private var closed = false
        override val source = FrameSourceKind.MEDIA_PROJECTION
        override val blindRects: List<PxRect> = emptyList()
        override val hardwareBuffer: HardwareBuffer? get() = if (closed) null else image.hardwareBuffer
        override val bitmap: Bitmap? = null

        @Synchronized
        override fun close() {
            if (closed) return
            closed = true
            image.close()
            gate.release()
        }
    }

    private inner class Port : DisplayPort {
        override fun create(size: FrameSize, dpi: Int) {
            val r = newReader(size)
            reader = r
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
            display?.resize(size.width, size.height, dpi)
            display?.setSurface(r.surface)
            old?.close()
        }
    }
}
