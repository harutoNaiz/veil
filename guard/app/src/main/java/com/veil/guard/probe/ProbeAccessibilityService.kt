package com.veil.guard.probe

import android.accessibilityservice.AccessibilityService
import android.util.Log
import android.view.accessibility.AccessibilityEvent

/** Phase 1.1 probe: proves a sideloaded app can be enabled as an accessibility service. It ignores everything. */
class ProbeAccessibilityService : AccessibilityService() {
    override fun onServiceConnected() {
        Log.i("VeilProbe", "VEIL_PROBE connected")
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {}

    override fun onInterrupt() {}
}
