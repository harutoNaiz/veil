package com.veil.guard.overlay

import android.content.Context
import android.content.res.Configuration
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Path
import android.graphics.Rect
import android.graphics.RectF
import android.os.SystemClock
import android.view.View
import android.view.WindowInsets
import android.view.WindowManager
import kotlin.math.roundToInt

/**
 * Draws device-pixel covers; one view for the whole display. Covers are frosted clouds (heavily averaged colours
 * of what lies under them, puffy feathered edges), never drawn over the status or navigation bars.
 */
class CoverView(context: Context) : View(context) {
    private val fill = Paint()
    private val text =
        Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.WHITE
            textAlign = Paint.Align.CENTER
        }
    private val noFilter = Paint().apply { isFilterBitmap = false }
    private val smooth = Paint(Paint.FILTER_BITMAP_FLAG or Paint.ANTI_ALIAS_FLAG)
    var crops: FrameCropSource? = null
    var samples: FrameSampleSource? = null

    private class Cloud(val bmp: Bitmap, val w: Int, val h: Int, val frameId: Long, val madeMs: Long)

    private val clouds = HashMap<Int, Cloud>()

    /** Calm on-screen covers (merged, steady, scroll-following, faded); set by the renderer. */
    var smoother: CoverSmoother? = null

    /** The covers to draw this frame, clipped to the content area, with their fade. */
    private fun current(now: Long): List<Triple<Cover, Px, Float>> {
        val content = contentArea()
        return smoother?.frame(now).orEmpty().mapNotNull { d ->
            clip(d.rect, content)?.let { Triple(d.cover, it, d.alpha) }
        }
    }

    fun drawnRects(): List<Px> = current(SystemClock.uptimeMillis()).map { it.second }

    /** Display area minus the visible system bars (status bar, navigation buttons, cutout band). */
    private fun contentArea(): Px {
        val metrics = context.getSystemService(WindowManager::class.java).currentWindowMetrics
        val w = if (width > 0) width else metrics.bounds.width()
        val h = if (height > 0) height else metrics.bounds.height()
        // Bar sizes ignoring visibility: the time/status strip and the back/home strip are never covered.
        val i = metrics.windowInsets.getInsetsIgnoringVisibility(
            WindowInsets.Type.systemBars() or WindowInsets.Type.displayCutout()
        )
        return Px(i.left, i.top, (w - i.left - i.right).coerceAtLeast(0), (h - i.top - i.bottom).coerceAtLeast(0))
    }

    private fun clip(r: Px, a: Px): Px? {
        val x0 = maxOf(r.x, a.x)
        val y0 = maxOf(r.y, a.y)
        val x1 = minOf(r.x + r.w, a.x + a.w)
        val y1 = minOf(r.y + r.h, a.y + a.h)
        return if (x1 - x0 < 8 || y1 - y0 < 8) null else Px(x0, y0, x1 - x0, y1 - y0)
    }

    override fun onDraw(canvas: Canvas) {
        text.textSize = 14f * resources.displayMetrics.scaledDensity
        val a = contentArea()
        canvas.save()
        canvas.clipRect(a.x, a.y, a.x + a.w, a.y + a.h) // the cloud's feathered rim never reaches the bars
        val now = SystemClock.uptimeMillis()
        val list = current(now)
        clouds.keys.retainAll(list.map { it.first.maskId }.toSet())
        for ((c, r, alpha) in list) {
            val dst = Rect(r.x, r.y, r.x + r.w, r.y + r.h)
            val faded = alpha < 0.999f
            if (faded) {
                canvas.saveLayerAlpha(
                    dst.left.toFloat(),
                    dst.top.toFloat(),
                    dst.right.toFloat(),
                    dst.bottom.toFloat(),
                    (
                        alpha *
                            255
                        ).toInt()
                )
            }
            when {
                c.label == "glue" -> solid(canvas, c, dst)
                c.style == CoverStyle.MOSAIC -> crops?.crop(r)?.let { mosaic(canvas, it, dst) } ?: cloud(canvas, c, r)
                else -> cloud(canvas, c, r)
            }
            c.label?.let { canvas.drawText(it, dst.exactCenterX(), dst.exactCenterY() + text.textSize / 3, text) }
            if (faded) canvas.restore()
        }
        canvas.restore()
        if (smoother?.animating(now) == true) postInvalidateOnAnimation()
    }

    /** "Sensitive content" veil: blurred own colours, evenly dimmed, rounded, exactly the cover rect, eye-off icon. */
    private fun cloud(canvas: Canvas, c: Cover, r: Px) {
        val density = resources.displayMetrics.density
        val snap = samples?.snapshot(r, width.coerceAtLeast(1), height.coerceAtLeast(1))
        val now = SystemClock.uptimeMillis()
        val old = clouds[c.maskId]
        val fresh = old != null && similar(old.w, r.w) && similar(old.h, r.h) &&
            (old.frameId == (snap?.id ?: -1L) || now - old.madeMs < REFRESH_MS)
        val bmp = if (fresh) {
            old!!.bmp
        } else {
            make(r, density, snap).also {
                clouds[c.maskId] = Cloud(it, r.w, r.h, snap?.id ?: -1L, now)
            }
        }
        val dst = RectF(r.x.toFloat(), r.y.toFloat(), (r.x + r.w).toFloat(), (r.y + r.h).toFloat())
        val radius = (12f * density).coerceAtMost(minOf(r.w, r.h) / 4f)
        canvas.save()
        clipPath.reset()
        clipPath.addRoundRect(dst, radius, radius, Path.Direction.CW)
        canvas.clipPath(clipPath)
        canvas.drawBitmap(bmp, null, dst, smooth)
        canvas.restore()
        label(canvas, dst, CoverNames.reason(context, c), density)
    }

    private val title =
        Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.WHITE
            textAlign = Paint.Align.CENTER
            typeface =
                android.graphics.Typeface.create(android.graphics.Typeface.DEFAULT, android.graphics.Typeface.BOLD)
            setShadowLayer(6f, 0f, 1f, 0x66000000)
        }
    private val reasonPaint =
        Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = 0xE6FFFFFF.toInt()
            textAlign = Paint.Align.CENTER
            setShadowLayer(6f, 0f, 1f, 0x66000000)
        }

    /** Instagram-style "sensitive content" badge: eye-off icon, "Hidden", and why (category or the user's word). */
    private fun label(canvas: Canvas, dst: RectF, reason: String, density: Float) {
        val short = minOf(dst.width(), dst.height())
        val s = (short * 0.10f).coerceIn(9f * density, 20f * density)
        val big = dst.height() >= 150f * density && dst.width() >= 150f * density
        val mid = !big && dst.height() >= 80f * density && dst.width() >= 110f * density
        title.textSize = (14f * density).coerceAtMost(short * 0.12f)
        reasonPaint.textSize = (12.5f * density).coerceAtMost(short * 0.11f)
        val maxW = dst.width() - 16f * density
        fun fit(p: Paint, t: String): String {
            if (p.measureText(t) <= maxW) return t
            var n = t.length
            while (n > 1 && p.measureText(t.take(n) + "…") > maxW) n--
            return t.take(n) + "…"
        }
        val cx = dst.centerX()
        when {
            big -> {
                val top =
                    dst.centerY() - (s * 1.1f + 6f * density + title.textSize + 4f * density + reasonPaint.textSize) / 2
                eyeOff(canvas, cx, top + s * 0.55f, s)
                val ty = top + s * 1.1f + 6f * density + title.textSize * 0.8f
                canvas.drawText("Hidden", cx, ty, title)
                canvas.drawText(fit(reasonPaint, reason), cx, ty + 4f * density + reasonPaint.textSize, reasonPaint)
            }

            mid -> {
                eyeOff(canvas, cx, dst.centerY() - reasonPaint.textSize * 0.6f, s)
                canvas.drawText(
                    fit(reasonPaint, reason),
                    cx,
                    dst.centerY() + s * 0.6f + reasonPaint.textSize * 0.7f,
                    reasonPaint
                )
            }

            else -> eyeOff(canvas, cx, dst.centerY(), s)
        }
    }

    private fun make(r: Px, density: Float, snap: FrameSnapshot?): Bitmap {
        val (gw, gh) = CloudMath.gridSize(r.w, r.h, density, MAX_TEXELS)
        val src = snap?.let { CloudMath.toFrame(r, it.screenW, it.screenH, it.w, it.h) }
        val grid =
            if (snap != null && src != null) {
                CloudMath.sampleGrid(snap.argb, snap.w, snap.h, src, gw, gh)
            } else {
                CloudMath.fallbackGrid(gw, gh, night())
            }
        val scale = (OUT_LONG / maxOf(r.w, r.h)).coerceAtMost(1f)
        val ow = (r.w * scale).roundToInt().coerceAtLeast(8)
        val oh = (r.h * scale).roundToInt().coerceAtLeast(8)
        val px = CloudMath.veil(grid, gw, gh, ow, oh, DIM_TO, DIM)
        return Bitmap.createBitmap(px, ow, oh, Bitmap.Config.ARGB_8888)
    }

    /** Within 25%: a sliding or growing cover reuses its texture (drawn scaled) instead of re-sampling every frame. */
    private fun similar(a: Int, b: Int) = kotlin.math.abs(a - b) * 4 <= maxOf(a, b)

    private fun night() =
        resources.configuration.uiMode and Configuration.UI_MODE_NIGHT_MASK == Configuration.UI_MODE_NIGHT_YES

    private val clipPath = Path()
    private val icon =
        Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = 0xE6FFFFFF.toInt()
            style = Paint.Style.STROKE
            strokeCap = Paint.Cap.ROUND
        }

    /** A small eye with a slash: "hidden by Veil". */
    private fun eyeOff(canvas: Canvas, cx: Float, cy: Float, s: Float) {
        icon.strokeWidth = s * 0.16f
        val eye = RectF(cx - s, cy - s * 0.55f, cx + s, cy + s * 0.55f)
        canvas.drawArc(eye, 200f, 140f, false, icon)
        canvas.drawArc(eye, 20f, 140f, false, icon)
        canvas.drawCircle(cx, cy, s * 0.22f, icon)
        canvas.drawLine(cx - s * 0.85f, cy + s * 0.75f, cx + s * 0.85f, cy - s * 0.75f, icon)
    }

    private fun solid(canvas: Canvas, c: Cover, dst: Rect) {
        fill.color = if (c.label == "glue") 0xFFE53935.toInt() else 0xFF202124.toInt()
        canvas.drawRect(dst, fill)
    }

    private fun mosaic(canvas: Canvas, bmp: Bitmap, dst: Rect) {
        val small = Bitmap.createScaledBitmap(bmp, maxOf(1, bmp.width / 16), maxOf(1, bmp.height / 16), true)
        canvas.drawBitmap(small, null, dst, noFilter)
    }

    private companion object {
        /** At most this many colour cells across a cover's long side: shapes and faces cannot survive. */
        const val MAX_TEXELS = 6
        const val OUT_LONG = 160f
        const val DIM_TO = 0xFF3A3F47.toInt()
        const val DIM = 0.45f
        const val REFRESH_MS = 2000L // colours of a playing video change constantly; a calm cover does not
    }
}
