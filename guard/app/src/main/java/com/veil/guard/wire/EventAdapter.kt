package com.veil.guard.wire

import com.veil.brain.contract.Rect
import com.veil.brain.contract.UiEvent as BrainEvent
import com.veil.conductor.LayoutNode
import com.veil.guard.signals.ContentChanged
import com.veil.guard.signals.NodesSnapshot
import com.veil.guard.signals.ScreenOff
import com.veil.guard.signals.ScreenOn
import com.veil.guard.signals.Scrolled
import com.veil.guard.signals.SnapNode
import com.veil.guard.signals.UiEvent as SignalEvent
import com.veil.guard.signals.WindowChanged

object EventAdapter {
    fun toBrain(e: SignalEvent): BrainEvent? = when (e) {
        is Scrolled -> BrainEvent("scrolled", e.tMs, e.dx, e.dy, e.packageName)
        is WindowChanged -> BrainEvent("windowChanged", e.tMs, 0, 0, e.packageName)
        is ContentChanged -> BrainEvent("contentChanged", e.tMs, 0, 0, e.packageName)
        is ScreenOff -> BrainEvent("screenOff", e.tMs, 0, 0, e.packageName)
        is ScreenOn -> BrainEvent("screenOn", e.tMs, 0, 0, e.packageName)
        is NodesSnapshot -> null
    }

    fun toLayout(n: SnapNode): LayoutNode = LayoutNode(n.kind, Rect(n.rect.x, n.rect.y, n.rect.w, n.rect.h), n.text)
}
