package com.veil.guard.overlay

import android.accessibilityservice.AccessibilityService
import android.view.accessibility.AccessibilityEvent
import com.veil.guard.signals.OverlayHostRegistry

/** Debug-only service for testing the overlay without the Guard service (Amendment A1). */
class OverlayAccessibilityService : AccessibilityService() {
    private val renderer = OverlayRenderer()

    override fun onServiceConnected() {
        OverlayHostRegistry.host = renderer
        renderer.onServiceConnected(this)
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) = Unit

    override fun onInterrupt() = Unit

    override fun onUnbind(intent: android.content.Intent?): Boolean {
        renderer.onServiceDisconnected()
        if (OverlayHostRegistry.host === renderer) OverlayHostRegistry.host = null
        return super.onUnbind(intent)
    }
}
