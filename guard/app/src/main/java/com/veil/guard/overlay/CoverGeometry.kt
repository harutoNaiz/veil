package com.veil.guard.overlay

object CoverGeometry {
    fun toDisplay(c: Px, plan: CoverPlan, d: DisplayState, padPx: Int = 0): Px? {
        var x0 = c.x
        var y0 = c.y
        var x1 = c.x + c.w
        var y1 = c.y + c.h
        var pw = plan.screenW
        var ph = plan.screenH
        val turns = Math.floorMod(d.rotation - plan.rotation, 4)
        repeat(turns) {
            // One display rotation step = 90 degrees counter-clockwise.
            val nx0 = y0
            val nx1 = y1
            val ny0 = pw - x1
            val ny1 = pw - x0
            x0 = nx0
            x1 = nx1
            y0 = ny0
            y1 = ny1
            val t = pw
            pw = ph
            ph = t
        }
        if (pw != d.w || ph != d.h) {
            val sx = d.w.toDouble() / pw
            val sy = d.h.toDouble() / ph
            x0 = Math.floor(x0 * sx).toInt()
            x1 = Math.ceil(x1 * sx).toInt()
            y0 = Math.floor(y0 * sy).toInt()
            y1 = Math.ceil(y1 * sy).toInt()
        }
        x0 = maxOf(0, x0 - padPx)
        y0 = maxOf(0, y0 - padPx)
        x1 = minOf(d.w, x1 + padPx)
        y1 = minOf(d.h, y1 + padPx)
        return if (x1 > x0 && y1 > y0) Px(x0, y0, x1 - x0, y1 - y0) else null
    }
}
