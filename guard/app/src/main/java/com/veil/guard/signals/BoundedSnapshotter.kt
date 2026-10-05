package com.veil.guard.signals

import android.os.Handler
import android.os.HandlerThread
import android.util.Log

/** Pull-only, budgeted layout snapshot. The only place that walks the accessibility tree. */
class BoundedSnapshotter(
    private val root: () -> SnapSourceNode?,
    private val clock: () -> Long,
    val budgetMs: Long = 40,
    val maxNodes: Int = 300,
    val minGapMs: Long = 250,
    private val ids: () -> Long = { 0 }
) : LayoutSnapshotter {
    private var last = Long.MIN_VALUE / 2
    private var thread: HandlerThread? = null

    @Synchronized
    override fun snapshot(): NodesSnapshot? {
        val start = clock()
        if (start - last < minGapMs) return null
        last = start
        val top = root()
        val nodes = ArrayList<SnapNode>()
        var truncated = false
        if (top != null) {
            val queue = ArrayDeque<SnapSourceNode>()
            queue.add(top)
            var visited = 0
            while (queue.isNotEmpty()) {
                if (clock() - start >= budgetMs || visited >= maxNodes) {
                    truncated = true
                    break
                }
                val n = queue.removeFirst()
                visited++
                if (!n.visible || n.rect.w <= 0 || n.rect.h <= 0) continue
                kindOf(n)?.let { nodes.add(toNode(it, n)) }
                for (i in 0 until n.childCount) n.child(i)?.let { queue.add(it) }
            }
        }
        val d = clock() - start
        log("VEIL_SNAP ms=$d nodes=${nodes.size} truncated=$truncated")
        return NodesSnapshot(ids(), start, null, nodes, truncated, d)
    }

    private fun toNode(kind: String, n: SnapSourceNode) =
        SnapNode(kind, n.rect, n.viewId, n.text?.take(MAX_TEXT), n.contentDescription?.take(MAX_DESC), n.className)

    private fun log(msg: String) {
        try {
            Log.i("VeilSnap", msg)
        } catch (_: RuntimeException) {
            // JVM unit tests: android.util.Log is a stub.
        }
    }

    fun startPump(sink: (UiEvent) -> Unit) {
        if (thread != null) return
        val t = HandlerThread("veil-snap-pump").also { it.start() }
        thread = t
        val h = Handler(t.looper)
        h.post(
            object : Runnable {
                override fun run() {
                    snapshot()?.let(sink)
                    h.postDelayed(this, minGapMs)
                }
            }
        )
    }

    fun stopPump() {
        thread?.quitSafely()
        thread = null
    }

    companion object {
        const val MAX_TEXT = 2000
        const val MAX_DESC = 500

        fun kindOf(n: SnapSourceNode): String? {
            val c = n.className ?: ""
            return when {
                c.contains("Image") -> "image"
                listOf("Video", "Surface", "Texture", "PlayerView").any { c.contains(it) } -> "video"
                c.contains("WebView") -> "web"
                !n.text.isNullOrBlank() -> "text"
                listOf("Recycler", "ListView", "Lazy").any { c.contains(it) } -> "list"
                else -> null
            }
        }
    }
}
