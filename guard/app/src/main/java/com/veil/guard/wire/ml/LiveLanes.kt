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
    private fun off(lane: String, why: String) {
        WireHub.log?.write(mapOf("kind" to "warn", "what" to "lane-off", "lane" to lane, "why" to why))
    }

    /** Re-reads models and concepts on every call. */
    fun build(ctx: Context, counters: Counters): List<Lane> {
        val store = ModelStore(ctx)
        val lanes = ArrayList<Lane>()
        val concepts = ConceptPack.load(File(ctx.externalMediaDirs.first(), "concepts"))
        val s320 = if (store.has("nudenet-320n.onnx")) store.session("nudenet-320n.onnx") else null
        if (s320 != null) {
            val s640 = if (store.has("nudenet-640m.onnx")) store.session("nudenet-640m.onnx") else null
            val large = s640?.let { OrtNsfwDetector("nudenet-640m", store.env, it, 640) }
            lanes += Layer1Lane(OrtNsfwDetector("nudenet-320n", store.env, s320, 320), large, counters)
        } else {
            off("layer1", "nudenet-320n.onnx missing")
        }
        val img = listOf(1, 4, 16).mapNotNull { b ->
            val n = "siglip2-image-b$b.onnx"
            if (store.has(n)) store.session(n)?.let { b to it } else null
        }.toMap()
        if (img.isNotEmpty() && concepts.describer.isNotEmpty()) {
            lanes += RegionLane(concepts, OrtDescriber(store.env, img), null, FingerprintCache(), counters)
        } else {
            off("region", if (img.isEmpty()) "siglip2 image models missing" else "no concepts")
        }
        lanes += TextLane(concepts, null, MlKitOcr(), counters)
        return lanes
    }
}
