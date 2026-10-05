package com.veil.guard.signals

data class PxRect(val x: Int, val y: Int, val w: Int, val h: Int)

data class SnapNode(
    val kind: String,
    val rect: PxRect,
    val nodeId: String? = null,
    val text: String? = null,
    val contentDescription: String? = null,
    val className: String? = null
) // kind: image|video|web|text|list|post|other

sealed interface UiEvent {
    val eventId: Long
    val tMs: Long
    val packageName: String?
}

data class Scrolled(
    override val eventId: Long,
    override val tMs: Long,
    override val packageName: String?,
    val dx: Int,
    val dy: Int,
    val containerRect: PxRect? = null,
    val containerId: String? = null,
    val estimated: Boolean = false
) : UiEvent

data class WindowChanged(
    override val eventId: Long,
    override val tMs: Long,
    override val packageName: String,
    val className: String? = null,
    val windowId: Int? = null
) : UiEvent

data class ContentChanged(
    override val eventId: Long,
    override val tMs: Long,
    override val packageName: String?,
    val rect: PxRect? = null,
    val changeTypes: List<String> = emptyList()
) : UiEvent

data class NodesSnapshot(
    override val eventId: Long,
    override val tMs: Long,
    override val packageName: String?,
    val nodes: List<SnapNode>,
    val truncated: Boolean,
    val durationMs: Long
) : UiEvent

data class ScreenOff(override val eventId: Long, override val tMs: Long, override val packageName: String? = null) :
    UiEvent

data class ScreenOn(override val eventId: Long, override val tMs: Long, override val packageName: String? = null) :
    UiEvent

/** Fields copied out of an AccessibilityEvent on the callback thread. No tree walk. -1 = not reported. */
data class RawEvent(
    val type: Int,
    val tMs: Long,
    val packageName: String?,
    val className: String?,
    val windowId: Int,
    val sourceKey: String?,
    val sourceRect: PxRect?,
    val scrollDeltaX: Int,
    val scrollDeltaY: Int,
    val scrollX: Int,
    val scrollY: Int,
    val maxScrollX: Int,
    val maxScrollY: Int,
    val contentChangeTypes: Int
)

data class ScrollDelta(val dx: Int, val dy: Int, val containerId: String?, val containerRect: PxRect?)

interface ScrollNormaliser {
    fun onScroll(raw: RawEvent): ScrollDelta? // content-moved sign

    fun reset()
}

interface SnapSourceNode {
    val rect: PxRect
    val className: String?
    val text: String?
    val contentDescription: String?
    val viewId: String?
    val visible: Boolean
    val childCount: Int

    fun child(i: Int): SnapSourceNode?
}

interface LayoutSnapshotter {
    fun snapshot(): NodesSnapshot? // null if < 250 ms since the last one; pull only
}

sealed interface ScreenshotResult {
    data class Ok(val bitmap: android.graphics.Bitmap, val tMs: Long) : ScreenshotResult

    data class Failed(val code: Int) : ScreenshotResult
}

/** Backup capture path for 4.1 (about 3 fps, no consent dialog). */
interface ScreenshotSource {
    val available: Boolean

    fun takeScreenshot(onResult: (ScreenshotResult) -> Unit)
}

object SignalsHub {
    @Volatile var screenshots: ScreenshotSource? = null

    @Volatile var snapshotter: LayoutSnapshotter? = null

    @Volatile var foregroundPackage: String? = null // set by the service while it is connected; null otherwise
}
