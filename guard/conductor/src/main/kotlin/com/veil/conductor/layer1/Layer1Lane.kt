package com.veil.conductor.layer1

import com.veil.brain.contract.Finding
import com.veil.brain.contract.Rect
import com.veil.brain.cover.iouPct
import com.veil.conductor.Counters
import com.veil.conductor.Lane
import com.veil.conductor.LookInput
import com.veil.conductor.NsfwBox
import com.veil.conductor.NsfwDetector
import com.veil.conductor.regions.PictureEdges

/**
 * Always-on safety layer: the small detector runs every look, the large one only in balanced and strict.
 * On a tall screen the small detector also reads square tiles, so a person inside a video player or a feed post is
 * seen at near-native size rather than squeezed with the whole screen. With [wholePicture], a hit covers the
 * picture it sits in (the app's image/video, else the picture's pixel edges), like a sensitive-content screen,
 * rather than only the body-part box.
 */
class Layer1Lane(
    private val small: NsfwDetector,
    private val large: NsfwDetector?,
    private val counters: Counters,
    private val thr: Double = 0.45,
    private val tiles: Boolean = false,
    private val wholePicture: Boolean = false,
    private val classes: Set<Int> = CLASSES
) : Lane {
    companion object {
        /** NudeNet label indices: BUTTOCKS_EXPOSED 2, FEMALE_BREAST_EXPOSED 3, FEMALE_GENITALIA_EXPOSED 4, ANUS_EXPOSED 6, MALE_GENITALIA_EXPOSED 14. */
        val CLASSES: Set<Int> = setOf(2, 3, 4, 6, 14)

        /** Child mode: also the covered sexual parts (genitalia 0, anus 15, breast 16, buttocks 17). */
        val CHILD_CLASSES: Set<Int> = CLASSES + setOf(0, 15, 16, 17)

        /** A picture larger than this share of the screen is the app itself, not a picture in it. */
        const val PICTURE_MAX_SCREEN_PCT = 60

        /** Square tiles covering a tall rect top to bottom (overlapping), or none when it is not tall. */
        fun tilesOf(r: Rect): List<Rect> {
            if (r.h < r.w * 3 / 2) return emptyList()
            val n = (r.h + r.w - 1) / r.w
            val step = (r.h - r.w) / (n - 1)
            return (0 until n).map { Rect(r.x, r.y + it * step, r.w, r.w) }
        }
    }

    override fun run(input: LookInput): List<Finding> {
        val boxes = ArrayList<NsfwBox>()
        counters.add("layer1.320n")
        boxes += small.detect(input.frame, input.rect)
        if (tiles) {
            for (t in tilesOf(input.rect)) {
                counters.add("layer1.tile")
                boxes += small.detect(input.frame, t)
            }
        }
        if (large != null && (input.mode == "balanced" || input.mode == "strict")) {
            counters.add("layer1.640m")
            boxes += large.detect(input.frame, input.rect)
        }
        val keep = ArrayList<NsfwBox>()
        for (b in boxes.filter { it.cls in classes && it.score >= thr }.sortedByDescending { it.score }) {
            if (keep.none { iouPct(it.rect, b.rect) >= 50 }) keep.add(b)
        }
        val m = input.frame.meta
        val out = ArrayList<Finding>()
        for (b in keep) {
            val r = if (wholePicture) picture(b.rect, input) else b.rect
            if (wholePicture && out.any { iouPct(it.rect, r) >= 50 }) continue
            out.add(
                Finding(
                    "l1-${input.lookId}-${out.size}", m.frameId, input.lookId, m.tMs, "layer1", 1, "hide",
                    b.score.toDouble(), r, "object", "layer1"
                )
            )
        }
        return out
    }

    private fun picture(b: Rect, input: LookInput): Rect {
        val sw = input.frame.meta.screenWidth.toLong()
        val sh = input.frame.meta.screenHeight.toLong()
        val cx = b.x + b.w / 2
        val cy = b.y + b.h / 2
        val node = input.layout.asSequence()
            .filter { it.kind == "image" || it.kind == "video" }
            .filter { cx >= it.rect.x && cx < it.rect.x + it.rect.w && cy >= it.rect.y && cy < it.rect.y + it.rect.h }
            .filter { it.rect.w.toLong() * it.rect.h * 100 <= sw * sh * PICTURE_MAX_SCREEN_PCT }
            .minByOrNull { it.rect.w.toLong() * it.rect.h }
        if (node != null && node.rect.w >= b.w && node.rect.h >= b.h) return node.rect
        // No picture reported: grow from a box three times the hit, stopping at the picture's flat edges.
        val x0 = maxOf(0, b.x - b.w)
        val y0 = maxOf(0, b.y - b.h)
        val x1 = minOf(sw.toInt(), b.x + 2 * b.w)
        val y1 = minOf(sh.toInt(), b.y + 2 * b.h)
        return PictureEdges.snap(input.frame, Rect(x0, y0, x1 - x0, y1 - y0))
    }
}
