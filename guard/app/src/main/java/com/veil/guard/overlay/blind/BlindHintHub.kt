package com.veil.guard.overlay.blind

import android.os.SystemClock
import com.veil.guard.capture.PxRect

/** Capture reports frame verdicts here; [listener] shows or hides the chip. */
object BlindHintHub {
    fun interface Listener {
        fun onVisible(visible: Boolean)
    }

    @Volatile var listener: Listener? = null

    @Volatile var foreground: () -> String? = { null }
    private val policy = BlindHintPolicy()
    private var last = false

    /** True when [blind] rects cover (nearly) the whole [w]x[h] frame. */
    fun isFullBlind(blind: List<PxRect>, w: Int, h: Int): Boolean =
        blind.any { it.w.toLong() * it.h >= w.toLong() * h * 9 / 10 }

    @Synchronized
    fun onFrame(blind: Boolean, nowMs: Long = SystemClock.uptimeMillis()) {
        val v = policy.onFrame(foreground(), blind, nowMs)
        if (v != last) {
            last = v
            listener?.onVisible(v)
        }
    }

    @Synchronized
    fun dismiss() {
        policy.dismiss()
        last = false
        listener?.onVisible(false)
    }
}
