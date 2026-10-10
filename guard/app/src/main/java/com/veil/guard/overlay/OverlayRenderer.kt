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
    private val smoother = CoverSmoother()
    private var ctx: Context? = null
    private val pillWins = HashMap<Int, android.view.View>()
    private val scrolls = com.veil.guard.signals.ScrollTracker()

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
        ctx = s
        val v = CoverView(s)
        v.smoother = smoother
        v.onFrame = { syncPills() }
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

    /** A raw scroll event (main thread): covers move with the content at once, before the next screenshot. */
    fun onScrollEvent(raw: com.veil.guard.signals.RawEvent) {
        val v = view ?: return
        val d = scrolls.onScroll(raw) ?: return
        smoother.onScroll(d.dx, d.dy, d.containerRect?.let { Px(it.x, it.y, it.w, it.h) })
        v.invalidate()
        syncPills()
    }

    /** One small touchable window per visible "Continue" pill; everything else stays pass-through. */
    private fun syncPills() {
        val v = view ?: return
        val w = wm ?: return
        val c = ctx ?: return
        val allowed = com.veil.guard.app.Parental.revealAllowed(c)
        v.revealOn = allowed
        val want = if (allowed) v.pills(SystemClock.uptimeMillis()).toMap() else emptyMap()
        for (id in pillWins.keys.filter { it !in want }) pillWins.remove(id)?.let { runCatching { w.removeView(it) } }
        for ((id, r) in want) {
            val pw = r.width().toInt()
            val ph = r.height().toInt()
            val existing = pillWins[id]
            if (existing == null) {
                val pv = android.view.View(c)
                pv.setOnClickListener {
                    smoother.reveal(id, SystemClock.uptimeMillis())
                    view?.invalidate()
                    syncPills()
                }
                pillWins[id] = pv
                runCatching { w.addView(pv, pillParams(r, pw, ph)) }.onFailure { pillWins.remove(id) }
            } else {
                val lp = existing.layoutParams as? WindowManager.LayoutParams ?: continue
                if (lp.x != r.left.toInt() || lp.y != r.top.toInt() || lp.width != pw || lp.height != ph) {
                    lp.x = r.left.toInt()
                    lp.y = r.top.toInt()
                    lp.width = pw
                    lp.height = ph
                    runCatching { w.updateViewLayout(existing, lp) }
                }
            }
        }
    }

    private fun pillParams(r: android.graphics.RectF, pw: Int, ph: Int): WindowManager.LayoutParams {
        val lp =
            WindowManager.LayoutParams(
                pw,
                ph,
                WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN or
                    WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,
                PixelFormat.TRANSLUCENT
            )
        lp.layoutInDisplayCutoutMode = WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_ALWAYS
        lp.fitInsetsTypes = 0
        lp.gravity = Gravity.TOP or Gravity.START
        lp.x = r.left.toInt()
        lp.y = r.top.toInt()
        return lp
    }

    private fun detach() {
        for (pv in pillWins.values) runCatching { wm?.removeView(pv) }
        pillWins.clear()
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
        // Every plan goes to the smoother, even an unchanged one: it may correct a cover a scroll moved.
        last = plan
        val m = v.resources.displayMetrics
        val display = wm?.defaultDisplay
        val ds = DisplayState(m.widthPixels, m.heightPixels, display?.rotation ?: Surface.ROTATION_0)
        v.crops = OverlayHub.crops
        v.samples = OverlayHub.samples
        val targets = plan.covers.mapNotNull { c -> CoverGeometry.toDisplay(c.rect, plan, ds)?.let { c to it } }
        smoother.onPlan(targets, ds.w.toLong() * ds.h, SystemClock.uptimeMillis())
        v.invalidate()
        syncPills()
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
