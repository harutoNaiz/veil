package com.veil.guard.overlay.touch

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.graphics.Path
import android.graphics.PixelFormat
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.view.Gravity
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import com.veil.guard.overlay.Cover
import com.veil.guard.overlay.CoverGesture
import com.veil.guard.overlay.OverlayHub
import java.io.File

/** One touchable window per peekable cover: taps/drags are replayed below, a hold is a LongPress. */
class CoverTouchLayer(private val service: AccessibilityService, private val logFile: File? = null) {
    private val wm = service.getSystemService(WindowManager::class.java)
    private val main = Handler(Looper.getMainLooper())
    private val windows = HashMap<Int, View>()

    fun update(covers: List<Cover>) {
        val wanted = covers.filter { it.peekable }.associateBy { it.maskId }
        windows.keys.filter { it !in wanted }.toList().forEach { windows.remove(it)?.let(wm::removeView) }
        for ((id, c) in wanted) {
            val params = paramsFor(c, touchable = true)
            val existing = windows[id]
            if (existing != null) {
                wm.updateViewLayout(existing, params)
            } else {
                val v = touchView(c)
                windows[id] = v
                wm.addView(v, params)
            }
        }
    }

    fun clear() {
        windows.values.forEach { runCatching { wm.removeView(it) } }
        windows.clear()
    }

    private fun paramsFor(c: Cover, touchable: Boolean): WindowManager.LayoutParams {
        var flags = WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS
        if (!touchable) flags = flags or WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE
        return WindowManager.LayoutParams(
            c.rect.w,
            c.rect.h,
            WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
            flags,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.START
            x = c.rect.x
            y = c.rect.y
        }
    }

    private fun touchView(c: Cover): View {
        val detector = LongPressDetector()
        val v = View(service)
        val holdCheck =
            object : Runnable {
                override fun run() {
                    detector.tick(SystemClock.uptimeMillis())?.let { lp ->
                        val g = CoverGesture.LongPress(c.maskId, lp.tMs, c.rect.x + lp.x, c.rect.y + lp.y)
                        logFile?.appendText("{\"type\":\"LongPress\",\"maskId\":${c.maskId},\"tMs\":${lp.tMs}}\n")
                        OverlayHub.gestureListeners.forEach { it(g) }
                    }
                }
            }
        v.setOnTouchListener { view, e ->
            val x = e.x.toInt() + c.rect.x
            val y = e.y.toInt() + c.rect.y
            val t = SystemClock.uptimeMillis()
            when (e.actionMasked) {
                MotionEvent.ACTION_DOWN -> {
                    detector.down(x, y, t)
                    main.postDelayed(holdCheck, 520)
                }

                MotionEvent.ACTION_MOVE -> detector.move(x, y, t)

                MotionEvent.ACTION_CANCEL -> {
                    main.removeCallbacks(holdCheck)
                    detector.cancel()
                }

                MotionEvent.ACTION_UP -> {
                    main.removeCallbacks(holdCheck)
                    detector.up(x, y, t)?.let { replay(view, c, it) }
                }
            }
            true
        }
        return v
    }

    private fun replay(view: View, c: Cover, r: TouchResult) {
        val strokes = TouchReplay.toStrokes(r)
        if (strokes.isEmpty()) return
        val b = GestureDescription.Builder()
        for (s in strokes) {
            val p = Path()
            s.path.forEachIndexed { i, (px, py) ->
                if (i ==
                    0
                ) {
                    p.moveTo(px.toFloat(), py.toFloat())
                } else {
                    p.lineTo(px.toFloat(), py.toFloat())
                }
            }
            if (s.path.size == 1) p.lineTo(s.path[0].first.toFloat() + 0.1f, s.path[0].second.toFloat())
            b.addStroke(GestureDescription.StrokeDescription(p, s.startMs, s.durationMs))
        }
        // let the gesture pass through our own window, then restore
        wm.updateViewLayout(view, paramsFor(c, touchable = false))
        val restore = {
            if (view.isAttachedToWindow) wm.updateViewLayout(view, paramsFor(c, touchable = true))
        }
        val cb =
            object : AccessibilityService.GestureResultCallback() {
                override fun onCompleted(g: GestureDescription?) = restore()

                override fun onCancelled(g: GestureDescription?) = restore()
            }
        if (!service.dispatchGesture(b.build(), cb, main)) restore()
    }
}
