package com.veil.guard.overlay

import android.accessibilityservice.AccessibilityService
import android.content.Context
import android.graphics.PixelFormat
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.view.Choreographer
import android.view.Gravity
import android.view.Surface
import android.view.WindowManager
import com.veil.guard.signals.OverlayHost
import java.io.File

/** Hosts the cover window inside whichever AccessibilityService calls onServiceConnected. */
class OverlayRenderer :
    OverlayHost,
    OverlaySink {
    private val main = Handler(Looper.getMainLooper())
    private var wm: WindowManager? = null
    private var view: CoverView? = null
    private var trace: RenderTrace? = null
    private var last: CoverPlan? = null

    override fun onServiceConnected(service: AccessibilityService) {
        main.post { attach(service) }
    }

    override fun onServiceDisconnected() {
        main.post { detach() }
    }

    override fun submit(plan: CoverPlan) {
        val recv = SystemClock.uptimeMillis()
        main.post { render(plan, recv) }
    }

    private fun attach(s: AccessibilityService) {
        trace = RenderTrace(File(s.filesDir, "overlay"))
        val w = s.getSystemService(Context.WINDOW_SERVICE) as WindowManager
        wm = w
        val v = CoverView(s)
        view = v
        val flags =
            WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE or WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN or WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS
        val lp =
            WindowManager.LayoutParams(
                WindowManager.LayoutParams.MATCH_PARENT,
                WindowManager.LayoutParams.MATCH_PARENT,
                WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
                flags,
                PixelFormat.TRANSLUCENT
            )
        lp.layoutInDisplayCutoutMode = WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_ALWAYS
        lp.fitInsetsTypes = 0
        lp.gravity = Gravity.TOP or Gravity.START
        w.addView(v, lp)
        OverlayHub.sink = this
        OverlayCommands.handlers["clear"] = { clear() }
    }

    private fun detach() {
        if (OverlayHub.sink === this) OverlayHub.sink = null
        view?.let { runCatching { wm?.removeView(it) } }
        view = null
        last = null
    }

    private fun clear() {
        val p = last ?: return
        submit(p.copy(covers = emptyList(), planId = p.planId + 1))
    }

    @Suppress("DEPRECATION")
    private fun render(plan: CoverPlan, recvMs: Long) {
        android.os.Trace.beginSection("veil.draw")
        try {
            renderInner(plan, recvMs)
        } finally {
            android.os.Trace.endSection()
        }
    }

    @Suppress("DEPRECATION")
    private fun renderInner(plan: CoverPlan, recvMs: Long) {
        val v = view ?: return
        val delta = PlanDiff.diff(last, plan)
        last = plan
        if (delta.isEmpty) return
        val m = v.resources.displayMetrics
        val display = wm?.defaultDisplay
        val ds = DisplayState(m.widthPixels, m.heightPixels, display?.rotation ?: Surface.ROTATION_0)
        v.crops = OverlayHub.crops
        v.samples = OverlayHub.samples
        v.setCovers(plan.covers.mapNotNull { c -> CoverGeometry.toDisplay(c.rect, plan, ds)?.let { c to it } })
        val rects = v.drawnRects()
        val period = 1000.0 / (display?.refreshRate ?: 60f)
        Choreographer.getInstance().postFrameCallback {
            val drawn = SystemClock.uptimeMillis()
            trace?.render(plan.planId, recvMs, drawn, period, plan.covers.size)
            val sample = OwnOverlaySample(drawn, rects)
            trace?.own(sample)
            OverlayHub.drawnListeners.forEach { it.onDrawn(sample) }
        }
    }
}
