package com.veil.conductor

import com.veil.brain.contract.CompiledConcept
import com.veil.brain.contract.Finding
import com.veil.brain.contract.FrameMeta
import com.veil.brain.contract.Record
import com.veil.brain.contract.Rect

/**
 * thumb = brain THUMB_W x THUMB_H gray; argb = frame-size pixels (null in pure tests). Rects everywhere are SCREEN px.
 * [showsOwnCovers]: the picture includes Veil's own covers (full-display shot), so it must not drive motion maps.
 */
class Frame(val meta: FrameMeta, val thumb: ByteArray, val argb: IntArray? = null, val showsOwnCovers: Boolean = false)

/** kind as 4.2 SnapNode: image|video|web|text|list|post|other */
data class LayoutNode(val kind: String, val rect: Rect, val text: String? = null)

enum class Source(val wire: String) { LAYOUT("layout"), FINDER("finder"), TILE("tile"), CROP("crop"), WHOLE("whole") }

data class Piece(
    val id: String,
    val rect: Rect,
    val source: Source,
    val kind: String,
    val lookId: Int,
    val parentId: String? = null
)

data class LookInput(val lookId: Int, val frame: Frame, val rect: Rect, val layout: List<LayoutNode>, val mode: String)

data class Concepts(
    val describer: List<CompiledConcept>,
    val finder: List<CompiledConcept>,
    val keywords: Map<String, List<String>>
)

/** Runs ON the AI worker. */
fun interface Lane {
    fun run(input: LookInput): List<Finding>
}

/** One call, pieces.size <= 16. */
interface Describer {
    fun describe(frame: Frame, pieces: List<Piece>): List<FloatArray>
}

/** Box + its own fingerprint. */
fun interface Finder {
    fun boxes(frame: Frame, area: Rect): List<Pair<Rect, FloatArray>>
}

data class NsfwBox(val cls: Int, val score: Float, val rect: Rect)

/** id: "nudenet-320n" | "nudenet-640m" */
interface NsfwDetector {
    val id: String

    fun detect(frame: Frame, area: Rect): List<NsfwBox>
}

fun interface Ocr {
    fun read(frame: Frame, rect: Rect): String?
}

fun interface TextClassifier {
    fun toxicity(text: String): Double
}

/** done receives findings and aiMs. */
interface AiWorker {
    val busy: Boolean

    fun submit(job: () -> List<Finding>, done: (List<Finding>, Long) -> Unit)
}

/** plan = mask-plan v1.0 map */
interface OverlayPort {
    fun submit(plan: Record)

    fun shift(dx: Int, dy: Int, tMs: Long)
}

fun interface StatsSink {
    fun publish(stats: Record)
}

/** One JSON line each: kind = look|finding|plan|stats|pause */
fun interface DebugLog {
    fun write(rec: Record)
}

class Counters {
    val m = java.util.concurrent.ConcurrentHashMap<String, Long>()

    fun add(k: String, n: Long = 1) {
        m.merge(k, n, Long::plus)
    }
}
