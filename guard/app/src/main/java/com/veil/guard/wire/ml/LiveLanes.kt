package com.veil.guard.wire.ml

import android.content.Context
import com.veil.brain.cache.FingerprintCache
import com.veil.conductor.Counters
import com.veil.conductor.Lane
import com.veil.conductor.layer1.Layer1Lane
import com.veil.conductor.regions.RegionLane
import com.veil.conductor.text.TextLane
import com.veil.guard.wire.MlKitOcr
import com.veil.guard.wire.WireHub
import java.io.File

object LiveLanes {
    private val fingerprints = FingerprintCache()

    private fun off(lane: String, why: String) {
        WireHub.log?.write(mapOf("kind" to "warn", "what" to "lane-off", "lane" to lane, "why" to why))
    }

    /** YOLOE boxes (variant C: described by SigLIP2, not judged by their own fingerprint). Null = tiles/layout only. */
    private fun openFinder(ctx: Context, store: ModelStore): OrtFinder? {
        if (!store.has(OrtFinder.MODEL)) {
            off("finder", "${OrtFinder.MODEL} missing")
            return null
        }
        return runCatching {
            val file = File(store.dir, OrtFinder.PE_FILE) // optional override next to the model
            val raw = if (file.isFile) file.readBytes() else ctx.assets.open(OrtFinder.PE_ASSET).use { it.readBytes() }
            val pe = OrtFinder.padPrompts(OrtFinder.parseNpy(raw))
            OrtFinder(store.env, store.session(OrtFinder.MODEL) ?: error("session"), pe)
        }.onFailure { off("finder", it.toString().take(120)) }.getOrNull()
    }

    /** "How to hide" as of the last lane build: whole picture/video (true) or just the object. */
    @Volatile var fullCover = true
        private set

    /** Re-reads models and concepts on every call. */
    fun build(ctx: Context, counters: Counters): List<Lane> {
        val store = ModelStore(ctx)
        val lanes = ArrayList<Lane>()
        val concepts = ConceptPack.load(File(ctx.externalMediaDirs.first(), "concepts"))
        val nudity = com.veil.guard.app.VeilSettings.nudity(ctx)
        val full = com.veil.guard.app.VeilSettings.fullCover(ctx)
        fullCover = full
        val s320 = if (nudity && store.has("nudenet-320n.onnx")) store.session("nudenet-320n.onnx") else null
        if (!nudity) {
            off("layer1", "turned off by the user (Nudity & explicit content)")
        } else if (s320 != null) {
            val s640 = if (store.has("nudenet-640m.onnx")) store.session("nudenet-640m.onnx") else null
            val large = s640?.let {
                OrtNsfwDetector("nudenet-640m", store.env, it, 640) { store.ready("nudenet-640m.onnx") }
            }
            lanes +=
                Layer1Lane(
                    OrtNsfwDetector("nudenet-320n", store.env, s320, 320) {
                        store.ready("nudenet-320n.onnx")
                    },
                    large,
                    counters,
                    tiles = true,
                    wholePicture = full
                )
        } else {
            off("layer1", "nudenet-320n.onnx missing")
        }
        val img = store.imageBatches().mapNotNull { b ->
            val n = "siglip2-image-b$b.onnx"
            if (store.has(n)) store.session(n)?.let { b to it } else null
        }.toMap()
        if (img.isNotEmpty() && concepts.describer.isNotEmpty()) {
            lanes +=
                RegionLane(
                    concepts,
                    OrtDescriber(store.env, img) {
                        store.readyImage()
                    },
                    openFinder(ctx, store), fingerprints, counters,
                    maxCoverScreenPct = 40, minCoverSidePx = 160, requireFine = true,
                    proposer = com.veil.conductor.regions.RegionProposer(minLayoutSidePx = 300),
                    snapPictures = full
                )
        } else {
            off("region", if (img.isEmpty()) "siglip2 image models missing" else "no concepts")
        }
        val tox = OrtToxicity.open(store)
        if (tox == null) off("toxicity", "toxicity-seq128.onnx or toxicity-tok.bin missing")
        lanes += TextLane(concepts, tox, MlKitOcr(), counters)
        store.warmUp() // QNN compile in the background; lanes hot-swap to it when ready
        return lanes
    }
}
