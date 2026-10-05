package com.veil.brain.contract

typealias Record = Map<String, Any?>

data class Rect(val x: Int, val y: Int, val w: Int, val h: Int) {
    fun toMap(): Record = linkedMapOf("x" to x, "y" to y, "w" to w, "h" to h)
}

data class UiEvent(
    val type: String,
    val tMs: Long,
    val dx: Int = 0,
    val dy: Int = 0,
    val packageName: String? = null,
    val raw: Record = emptyMap()
)

data class FrameMeta(
    val frameId: Int,
    val tMs: Long,
    val width: Int,
    val height: Int,
    val screenWidth: Int,
    val screenHeight: Int,
    val ownOverlay: List<Rect>
)

data class Finding(
    val findingId: String,
    val frameId: Int,
    val lookId: Int,
    val tMs: Long,
    val conceptId: String,
    val layer: Int,
    val decision: String,
    val probability: Double,
    val rect: Rect,
    val scope: String,
    val lane: String
)

data class Track(
    val trackId: Int,
    val conceptId: String,
    val layer: Int,
    val rect: Rect,
    val state: String,
    val sightings: Int,
    val firstSeenMs: Long,
    val lastSeenMs: Long,
    val holdUntilMs: Long,
    val maxHoldUntilMs: Long,
    val lastFindingId: String,
    val peeked: Boolean,
    val scope: String,
    val selfCaptureFraction: Double
) {
    fun toMap(): Record = linkedMapOf(
        "trackId" to trackId, "conceptId" to conceptId, "layer" to layer, "rect" to rect.toMap(),
        "state" to state, "sightings" to sightings, "firstSeenMs" to firstSeenMs, "lastSeenMs" to lastSeenMs,
        "holdUntilMs" to holdUntilMs, "maxHoldUntilMs" to maxHoldUntilMs, "lastFindingId" to lastFindingId,
        "peeked" to peeked, "scope" to scope, "selfCaptureFraction" to selfCaptureFraction
    )
}

data class Embedding(val dim: Int, val vectorF16: String, val raw: Record = emptyMap())

data class CompiledConcept(
    val conceptId: String,
    val looksLike: List<Embedding>,
    val butNot: List<Embedding>,
    val ignore: List<Embedding>,
    val calibrationOffset: Double,
    val userOffset: Double,
    val thresholds: Map<String, Double>,
    val margin: Double,
    val exampleCentroid: Embedding? = null,
    val exampleThreshold: Double? = null,
    val raw: Record = emptyMap()
)

data class Verdict(
    val pRaw: Double,
    val probability: Double,
    val score: Double,
    val margin: Double,
    val decision: String,
    val exampleScore: Double? = null
)
