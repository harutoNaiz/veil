package com.veil.guard.bridge

data class BridgeConcept(val conceptId: String, val displayName: String, val enabled: Boolean)

data class BridgeState(
    val running: Boolean,
    val mode: String,
    val captureState: String,
    val permissions: Map<String, Boolean>,
    val skipList: List<String>,
    val concepts: List<BridgeConcept>,
    val activePackSha256: String?
)

data class BridgeCover(val coverId: String, val conceptId: String, val tMs: Long)

/** What the Console may ask of the Guard. Android implementation: [AndroidBridgeOps]. */
interface BridgeOps {
    fun state(): BridgeState

    fun start()

    fun pause()

    fun resume()

    fun stop()

    fun setMode(mode: String)

    fun setSkipList(packages: List<String>)

    fun installPack(json: String)

    fun recentCovers(limit: Int): List<BridgeCover>
}
