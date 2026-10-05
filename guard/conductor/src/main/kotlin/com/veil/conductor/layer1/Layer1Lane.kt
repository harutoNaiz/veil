package com.veil.conductor.layer1

import com.veil.brain.contract.Finding
import com.veil.brain.cover.iouPct
import com.veil.conductor.Counters
import com.veil.conductor.Lane
import com.veil.conductor.LookInput
import com.veil.conductor.NsfwBox
import com.veil.conductor.NsfwDetector

/** Always-on safety layer: the small detector runs every look, the large one only in balanced and strict. */
class Layer1Lane(
    private val small: NsfwDetector,
    private val large: NsfwDetector?,
    private val counters: Counters,
    private val thr: Double = 0.45
) : Lane {
    companion object {
        /** NudeNet label indices: BUTTOCKS_EXPOSED 2, FEMALE_BREAST_EXPOSED 3, FEMALE_GENITALIA_EXPOSED 4, ANUS_EXPOSED 6, MALE_GENITALIA_EXPOSED 14. */
        val CLASSES: Set<Int> = setOf(2, 3, 4, 6, 14)
    }

    override fun run(input: LookInput): List<Finding> {
        val boxes = ArrayList<NsfwBox>()
        counters.add("layer1.320n")
        boxes += small.detect(input.frame, input.rect)
        if (large != null && (input.mode == "balanced" || input.mode == "strict")) {
            counters.add("layer1.640m")
            boxes += large.detect(input.frame, input.rect)
        }
        val keep = ArrayList<NsfwBox>()
        for (b in boxes.filter { it.cls in CLASSES && it.score >= thr }.sortedByDescending { it.score }) {
            if (keep.none { iouPct(it.rect, b.rect) >= 50 }) keep.add(b)
        }
        val m = input.frame.meta
        return keep.mapIndexed { i, b ->
            Finding(
                "l1-${input.lookId}-$i", m.frameId, input.lookId, m.tMs, "layer1", 1, "hide",
                b.score.toDouble(), b.rect, "object", "layer1"
            )
        }
    }
}
