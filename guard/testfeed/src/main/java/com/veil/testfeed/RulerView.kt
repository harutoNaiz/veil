package com.veil.testfeed

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.view.View

/**
 * A ruler for checking positions: a 1 px tick every 10 px (20 px long) and a 60 px tick with a label "<px>" every
 * 100 px, along the left edge (vertical position) and the top edge (horizontal position). Distances are in px
 * from the view's own top-left corner.
 */
class RulerView(context: Context) : View(context) {
    private val tickPaint =
        Paint().apply {
            color = Color.BLACK
            strokeWidth = 1f
            isAntiAlias = false
        }
    private val textPaint =
        Paint().apply {
            color = Color.BLACK
            textSize = LABEL_SIZE_PX
            isAntiAlias = true
        }

    init {
        setBackgroundColor(Color.WHITE)
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        var pos = 0
        while (pos < height || pos < width) {
            val major = pos % MAJOR_STEP == 0
            val length = (if (major) MAJOR_LENGTH else MINOR_LENGTH).toFloat()
            if (pos < height) {
                canvas.drawLine(0f, pos + HALF, length, pos + HALF, tickPaint)
                if (major) canvas.drawText(pos.toString(), length + LABEL_GAP, pos + LABEL_SIZE_PX, textPaint)
            }
            if (pos < width) {
                canvas.drawLine(pos + HALF, 0f, pos + HALF, length, tickPaint)
                if (major && pos > 0) {
                    canvas.drawText(pos.toString(), pos + LABEL_GAP, length + LABEL_SIZE_PX, textPaint)
                }
            }
            pos += MINOR_STEP
        }
    }

    private companion object {
        const val MINOR_STEP = 10
        const val MAJOR_STEP = 100
        const val MINOR_LENGTH = 20
        const val MAJOR_LENGTH = 60
        const val LABEL_SIZE_PX = 28f
        const val LABEL_GAP = 6f
        const val HALF = 0.5f
    }
}
