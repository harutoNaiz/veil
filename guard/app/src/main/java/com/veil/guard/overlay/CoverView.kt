package com.veil.guard.overlay

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Rect
import android.graphics.RectF
import android.graphics.RenderEffect
import android.graphics.RenderNode
import android.graphics.Shader
import android.view.View

/** Draws device-pixel covers; one view for the whole display. */
class CoverView(context: Context) : View(context) {
    private var covers: List<Pair<Cover, Px>> = emptyList()
    private val fill = Paint()
    private val text =
        Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.WHITE
            textAlign = Paint.Align.CENTER
        }
    private val noFilter = Paint().apply { isFilterBitmap = false }
    var crops: FrameCropSource? = null

    fun setCovers(list: List<Pair<Cover, Px>>) {
        covers = list.sortedBy { it.first.layer }
        invalidate()
    }

    fun drawnRects(): List<Px> = covers.map { it.second }

    override fun onDraw(canvas: Canvas) {
        text.textSize = 14f * resources.displayMetrics.scaledDensity
        for ((c, r) in covers) {
            val dst = Rect(r.x, r.y, r.x + r.w, r.y + r.h)
            val bmp = if (c.style == CoverStyle.SOLID) null else crops?.crop(r)
            when {
                bmp == null -> solid(canvas, c, dst)
                c.style == CoverStyle.MOSAIC -> mosaic(canvas, bmp, dst)
                else -> blur(canvas, bmp, dst)
            }
            c.label?.let { canvas.drawText(it, dst.exactCenterX(), dst.exactCenterY() + text.textSize / 3, text) }
        }
    }

    private fun solid(canvas: Canvas, c: Cover, dst: Rect) {
        fill.color = if (c.label == "glue") 0xFFE53935.toInt() else 0xFF202124.toInt()
        canvas.drawRect(dst, fill)
    }

    private fun mosaic(canvas: Canvas, bmp: Bitmap, dst: Rect) {
        val small = Bitmap.createScaledBitmap(bmp, maxOf(1, bmp.width / 16), maxOf(1, bmp.height / 16), true)
        canvas.drawBitmap(small, null, dst, noFilter)
    }

    private fun blur(canvas: Canvas, bmp: Bitmap, dst: Rect) {
        val node = RenderNode("blur")
        node.setPosition(0, 0, dst.width(), dst.height())
        node.setRenderEffect(RenderEffect.createBlurEffect(25f, 25f, Shader.TileMode.CLAMP))
        val rc = node.beginRecording()
        rc.drawBitmap(bmp, null, RectF(0f, 0f, dst.width().toFloat(), dst.height().toFloat()), null)
        node.endRecording()
        canvas.save()
        canvas.translate(dst.left.toFloat(), dst.top.toFloat())
        canvas.clipRect(0, 0, dst.width(), dst.height())
        canvas.drawRenderNode(node)
        canvas.restore()
    }
}
