package com.veil.guard.wire

import android.os.Handler
import android.os.Looper
import android.os.Trace
import com.veil.brain.contract.Record
import com.veil.conductor.OverlayPort
import com.veil.guard.overlay.CoverPlan
import com.veil.guard.overlay.OverlayHub
import com.veil.guard.overlay.OwnOverlayListener
import com.veil.guard.overlay.touch.CoverTouchLayer

class LiveOverlay(private val touch: CoverTouchLayer) : OverlayPort {
    private val main = Handler(Looper.getMainLooper())

    @Volatile private var last: CoverPlan? = null

    @Volatile private var pendingDraw = false
    private val listener = OwnOverlayListener { s ->
        if (pendingDraw) {
            pendingDraw = false
            WireHub.drawn?.invoke(s.tMs)
        }
    }

    init {
        OverlayHub.drawnListeners.add(listener)
    }

    override fun submit(plan: Record) {
        Trace.beginSection("veil.plan")
        try {
            send(PlanRecords.toCoverPlan(plan), true)
        } finally {
            Trace.endSection()
        }
    }

    override fun shift(dx: Int, dy: Int, tMs: Long) {
        val l = last ?: return
        send(PlanRecords.shifted(l, dx, dy), false)
    }

    fun close() {
        OverlayHub.drawnListeners.remove(listener)
    }

    private fun send(cp: CoverPlan, arm: Boolean) {
        val sink = OverlayHub.sink
        if (sink == null) {
            WireHub.log?.write(mapOf("kind" to "warn", "what" to "overlay sink missing"))
        } else {
            if (arm) pendingDraw = true
            sink.submit(cp)
        }
        last = cp
        main.post { runCatching { touch.update(cp.covers) } }
    }
}
