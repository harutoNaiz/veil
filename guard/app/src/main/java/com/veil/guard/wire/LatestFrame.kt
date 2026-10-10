package com.veil.guard.wire

import com.veil.guard.overlay.FrameSampleSource
import com.veil.guard.overlay.FrameSnapshot
import com.veil.guard.overlay.OverlayHub
import com.veil.guard.overlay.Px

/**
 * Last captured frame, kept for the cloud covers' colours. Window screenshots never hold our covers; a display
 * mirror may, in which case the cloud samples itself, which only ever makes it more uniform (never sharper).
 */
object LatestFrame : FrameSampleSource {
    @Volatile private var snap: FrameSnapshot? = null
    private var id = 0L

    fun publish(argb: IntArray, w: Int, h: Int, screenW: Int, screenH: Int) {
        snap = FrameSnapshot(++id, argb, w, h, screenW, screenH)
        if (OverlayHub.samples == null) OverlayHub.samples = this
    }

    /** Debug: writes the last captured frame (what the guard actually sees) as a PNG. */
    fun save(f: java.io.File) {
        val s = snap ?: return
        val bm = android.graphics.Bitmap.createBitmap(s.argb, s.w, s.h, android.graphics.Bitmap.Config.ARGB_8888)
        f.outputStream().use { bm.compress(android.graphics.Bitmap.CompressFormat.PNG, 100, it) }
        bm.recycle()
    }

    override fun snapshot(rect: Px, dispW: Int, dispH: Int): FrameSnapshot? = snap
}
