package com.veil.guard.overlay
data class Px(val x: Int, val y: Int, val w: Int, val h: Int)
enum class CoverStyle { SOLID, BLUR, MOSAIC }
data class Cover(
    val maskId: Int,
    val rect: Px,
    val style: CoverStyle,
    val layer: Int,
    val peekable: Boolean,
    val label: String? = null
)
data class CoverPlan(
    val planId: Long,
    val tMs: Long,
    val screenW: Int,
    val screenH: Int,
    val rotation: Int,
    val covers: List<Cover>,
    val reason: String
) // mirrors mask-plan.schema.json v1.0 (extra mask fields ignored)
data class DisplayState(val w: Int, val h: Int, val rotation: Int)

/** Pure. Covers that changed (added, removed, moved, restyled); empty = no redraw. */
data class PlanDelta(val added: List<Cover>, val removed: List<Int>, val changed: List<Cover>) {
    val isEmpty get() = added.isEmpty() &&
        removed.isEmpty() &&
        changed.isEmpty()
}
interface OverlaySink {
    fun submit(plan: CoverPlan)
} // OverlayRenderer implements; any thread
fun interface FrameCropSource {
    fun crop(rect: Px): android.graphics.Bitmap?
}
data class OwnOverlaySample(val tMs: Long, val rects: List<Px>) // what was actually on screen from tMs on
fun interface OwnOverlayListener {
    fun onDrawn(sample: OwnOverlaySample)
} // called after each drawn frame
sealed interface CoverGesture {
    val maskId: Int
    val tMs: Long
    data class LongPress(override val maskId: Int, override val tMs: Long, val x: Int, val y: Int) : CoverGesture
}
object OverlayHub {
    @Volatile var sink: OverlaySink? = null

    @Volatile var crops: FrameCropSource? = null
    val drawnListeners = java.util.concurrent.CopyOnWriteArrayList<OwnOverlayListener>()
    val gestureListeners = java.util.concurrent.CopyOnWriteArrayList<(CoverGesture) -> Unit>()
}
object OverlayCommands {
    val handlers = java.util.concurrent.ConcurrentHashMap<String, (String?) -> Unit>()
}
