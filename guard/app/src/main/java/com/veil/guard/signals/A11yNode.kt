package com.veil.guard.signals

import android.accessibilityservice.AccessibilityService
import android.graphics.Rect
import android.view.accessibility.AccessibilityNodeInfo

/** Adapts an AccessibilityNodeInfo to [SnapSourceNode]. Only BoundedSnapshotter walks it (pull only). */
class A11yNode(private val info: AccessibilityNodeInfo) : SnapSourceNode {
    override val rect: PxRect
        get() {
            val r = Rect()
            info.getBoundsInScreen(r)
            return PxRect(r.left, r.top, r.width(), r.height())
        }
    override val className: String? get() = info.className?.toString()
    override val text: String? get() = info.text?.toString()
    override val contentDescription: String? get() = info.contentDescription?.toString()
    override val viewId: String? get() = info.viewIdResourceName
    override val visible: Boolean get() = info.isVisibleToUser
    override val childCount: Int get() = info.childCount

    override fun child(i: Int): SnapSourceNode? = info.getChild(i)?.let { A11yNode(it) }

    companion object {
        /** Root provider for BoundedSnapshotter. Kept here so the service callbacks hold no tree access. */
        fun rootOf(service: AccessibilityService): () -> SnapSourceNode? =
            { service.rootInActiveWindow?.let { A11yNode(it) } }
    }
}
