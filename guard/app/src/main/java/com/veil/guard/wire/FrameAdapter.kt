package com.veil.guard.wire

import android.graphics.Bitmap
import android.graphics.ColorSpace
import android.os.SystemClock
import android.os.Trace
import com.veil.brain.contract.FrameMeta
import com.veil.brain.contract.Rect
import com.veil.conductor.Frame
import com.veil.conductor.Thumbs
import com.veil.guard.capture.CapturedFrame
import com.veil.guard.capture.FrameSink
import com.veil.guard.overlay.self.SelfCapture

/** Capture sink: copies the frame to an IntArray, closes it at once, restamps with uptime, hands a Frame to the hub. */
object FrameAdapter {
    private var id = 0

    val sink: FrameSink =
        FrameSink { frame -> handle(frame) }

    private fun handle(frame: CapturedFrame) {
        val cb = WireHub.frames
        if (cb == null) {
            frame.close()
            return
        }
        Trace.beginSection("veil.frame")
        try {
            val w = frame.size.width
            val h = frame.size.height
            val argb: IntArray
            try {
                val hb = frame.hardwareBuffer
                var src: Bitmap? = null
                var soft: Bitmap? = null
                try {
                    src =
                        if (hb != null) {
                            Bitmap.wrapHardwareBuffer(hb, ColorSpace.get(ColorSpace.Named.SRGB))
                        } else {
                            frame.bitmap
                        }
                    if (src == null) {
                        WireHub.log?.write(mapOf("kind" to "warn", "what" to "frame-no-bitmap"))
                        return
                    }
                    soft = src.copy(Bitmap.Config.ARGB_8888, false)
                    if (soft == null) {
                        WireHub.log?.write(mapOf("kind" to "warn", "what" to "frame-copy-failed"))
                        return
                    }
                    argb = IntArray(soft.width * soft.height)
                    soft.getPixels(argb, 0, soft.width, 0, 0, soft.width, soft.height)
                } finally {
                    soft?.recycle()
                    // a11y bitmaps are owned by their frame; only recycle what we wrapped
                    if (hb != null) src?.recycle()
                    // Image.getHardwareBuffer() hands out a new reference per call that must be closed
                    hb?.close()
                }
            } finally {
                frame.close()
            }
            val t = SystemClock.uptimeMillis()
            val own = SelfCapture.current?.at(t)?.map { Rect(it.x, it.y, it.w, it.h) } ?: emptyList()
            val meta = FrameMeta(++id, t, w, h, frame.screen.width, frame.screen.height, own)
            LatestFrame.publish(argb, w, h, frame.screen.width, frame.screen.height)
            cb(Frame(meta, Thumbs.fromArgb(argb, w, h), argb))
        } finally {
            Trace.endSection()
        }
    }
}
