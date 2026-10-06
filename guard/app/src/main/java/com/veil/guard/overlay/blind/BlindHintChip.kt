package com.veil.guard.overlay.blind

import android.content.Context
import android.graphics.PixelFormat
import android.view.Gravity
import android.view.WindowManager
import android.widget.TextView
import com.veil.guard.R

/** Small non-blocking dismissible chip; tap to close for this app. */
class BlindHintChip(private val ctx: Context) : BlindHintHub.Listener {
    private val wm = ctx.getSystemService(Context.WINDOW_SERVICE) as WindowManager
    private var view: TextView? = null

    override fun onVisible(visible: Boolean) {
        android.os.Handler(android.os.Looper.getMainLooper()).post { if (visible) show() else hide() }
    }

    private fun show() {
        if (view != null) return
        val tv =
            TextView(ctx).apply {
                text = ctx.getString(R.string.blind_hint_text)
                setTextColor(0xFFFFFFFF.toInt())
                setBackgroundColor(0xCC222222.toInt())
                setPadding(32, 16, 32, 16)
                setOnClickListener { BlindHintHub.dismiss() }
            }
        val lp =
            WindowManager.LayoutParams(
                WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
                PixelFormat.TRANSLUCENT
            ).apply {
                gravity = Gravity.TOP or Gravity.CENTER_HORIZONTAL
                y = 96
            }
        runCatching { wm.addView(tv, lp) }.onSuccess { view = tv }
    }

    private fun hide() {
        view?.let { runCatching { wm.removeView(it) } }
        view = null
    }
}
