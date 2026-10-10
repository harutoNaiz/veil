package com.veil.guard.overlay

/**
 * Pure: turns the engine's cover plans into calm on-screen covers.
 *
 * The engine re-judges the screen about once a second and each look may box the same picture a little
 * differently (an autoplaying video preview changes its pixels, so its found edges change every look). Drawn as
 * is, covers jitter in size, stack on top of each other and jump during scrolls. Here:
 *  - a cover that matches one already shown keeps its place and only ever grows while the page is still (the
 *    union of what was shown and what is found), so a video preview stays one steady block;
 *  - covers that overlap are merged into one rectangle, never stacked;
 *  - covers follow scrolling at once from the accessibility scroll deltas (between screenshots), and the next
 *    plan corrects the rest with a short slide rather than a jump;
 *  - covers fade in and out instead of popping.
 * All times are uptime milliseconds; rects are display pixels.
 */
class CoverSmoother(private val fadeMs: Long = 180, private val moveMs: Long = 140) {
    data class Drawn(val cover: Cover, val rect: Px, val alpha: Float, val live: Boolean = true)

    private class Shown(
        val id: Int,
        var cover: Cover,
        var from: Px,
        var to: Px,
        var moveStart: Long,
        var born: Long,
        var dying: Long = -1,
        var revealed: Boolean = false
    )

    private val shown = ArrayList<Shown>()
    private var nextId = 1

    /** A new plan: [targets] are the engine's covers in display pixels; [screenArea] bounds merging. */
    fun onPlan(targets: List<Pair<Cover, Px>>, screenArea: Long, now: Long) {
        val merged = merge(targets, screenArea)
        val used = HashSet<Shown>()
        // A revealed cover stays revealed while the engine keeps finding it; it is forgotten once it is gone.
        val open = merged.filter { (_, t) ->
            val r = shown.filter { it.revealed && it !in used }.maxByOrNull { inter(it.to, t) }
                ?.takeIf { overlapFrac(it.to, t) >= MATCH }
            if (r != null) {
                used.add(r)
                r.from = t
                r.to = t
            }
            r == null
        }
        shown.removeAll { it.revealed && it !in used }
        for ((c, t) in open.sortedByDescending { area(it.second) }) {
            val s = shown.filter { it !in used && !it.revealed && alpha(it, now) > 0f }
                .maxByOrNull { inter(cur(it, now), t) }
                ?.takeIf { overlapFrac(cur(it, now), t) >= MATCH }
            if (s == null) {
                used.add(Shown(nextId++, c, t, t, now, now).also { shown.add(it) })
                continue
            }
            used.add(s)
            val r = cur(s, now)
            if (s.dying >= 0) { // back before it faded out: keep fading in from where it is
                s.born = now - (fadeMs * alpha(s, now)).toLong()
                s.dying = -1
            }
            val u = union(r, t)
            val next = if (still(r, t) && area(u) <= area(t) * GROW_CAP) u else t
            s.cover = c.copy(concepts = (s.cover.concepts + c.concepts).distinct().take(4))
            moveTo(s, r, next, now)
        }
        for (s in shown) if (s.dying < 0 && s !in used) s.dying = now
        mergeShown(screenArea, now)
    }

    /** Content inside [container] (null = anywhere) moved by (dx, dy): covers move with it at once. */
    fun onScroll(dx: Int, dy: Int, container: Px?) {
        if (kotlin.math.abs(dx) <= 1 && kotlin.math.abs(dy) <= 1) return // sign-only jitter events
        for (s in shown) {
            val c = s.to
            val cx = c.x + c.w / 2
            val cy = c.y + c.h / 2
            if (container != null &&
                (
                    cx < container.x || cx >= container.x + container.w || cy < container.y ||
                        cy >= container.y + container.h
                    )
            ) {
                continue
            }
            s.from = s.from.copy(x = s.from.x + dx, y = s.from.y + dy)
            s.to = s.to.copy(x = s.to.x + dx, y = s.to.y + dy)
        }
    }

    /** What to draw now (covers keep a stable id as maskId, so their cloud textures are reused). */
    fun frame(now: Long): List<Drawn> {
        shown.removeAll { it.dying >= 0 && !it.revealed && now - it.dying >= fadeMs }
        return shown.filter { !it.revealed || now - it.dying < fadeMs }
            .map { s -> Drawn(s.cover.copy(maskId = s.id), cur(s, now), alpha(s, now), s.dying < 0) }
            .sortedBy { it.cover.layer }
    }

    /** True while a fade or slide is running (keep drawing frames). */
    fun animating(now: Long): Boolean = shown.any { s ->
        (s.dying >= 0 && now - s.dying < fadeMs) || now - s.born < fadeMs ||
            (now - s.moveStart < moveMs && s.from != s.to)
    }

    /** The user chose "Continue" on cover [id]: it fades out and stays hidden until the engine stops finding it. */
    fun reveal(id: Int, now: Long) {
        val s = shown.firstOrNull { it.id == id && !it.revealed } ?: return
        s.revealed = true
        s.dying = now
    }

    /** Where cover [id] is now (display px), or null. */
    fun rectOf(id: Int): Px? = shown.firstOrNull { it.id == id }?.to

    fun revealedIds(): Set<Int> = shown.filter { it.revealed }.map { it.id }.toSet()

    private fun moveTo(s: Shown, at: Px, next: Px, now: Long) {
        if (next == s.to) return
        s.from = at
        s.to = next
        s.moveStart = now
    }

    private fun alpha(s: Shown, now: Long): Float {
        val inA = ((now - s.born).toFloat() / fadeMs).coerceIn(0f, 1f)
        val outA = if (s.dying < 0) 1f else (1f - (now - s.dying).toFloat() / fadeMs).coerceIn(0f, 1f)
        return inA * outA
    }

    private fun cur(s: Shown, now: Long): Px {
        if (s.from == s.to) return s.to
        val t = ((now - s.moveStart).toFloat() / moveMs).coerceIn(0f, 1f)
        if (t >= 1f) return s.to
        val e = 1f - (1f - t) * (1f - t) // ease out
        fun l(a: Int, b: Int) = a + ((b - a) * e).toInt()
        return Px(l(s.from.x, s.to.x), l(s.from.y, s.to.y), l(s.from.w, s.to.w), l(s.from.h, s.to.h))
    }

    /** Shown covers that came to overlap (one grew, or a scroll pushed them together) become one. */
    private fun mergeShown(screenArea: Long, now: Long) {
        var changed = true
        while (changed) {
            changed = false
            val live = shown.filter { it.dying < 0 }
            loop@ for (i in live.indices) {
                for (j in i + 1 until live.size) {
                    val a = live[i]
                    val b = live[j]
                    if (inter(a.to, b.to) == 0L) continue
                    val u = union(a.to, b.to)
                    if (area(u) * 100 > screenArea * MAX_MERGE_SCREEN_PCT) continue
                    val keep = if (a.born <= b.born) a else b
                    val gone = if (keep === a) b else a
                    keep.cover = mergedCover(keep.cover, gone.cover)
                    moveTo(keep, cur(keep, now), u, now)
                    shown.remove(gone)
                    changed = true
                    break@loop
                }
            }
        }
    }

    companion object {
        /** A found cover is the shown one when they overlap by this share of the smaller. */
        const val MATCH = 0.3

        /** While still, a cover grows to cover old + new, unless that is this many times the new box. */
        const val GROW_CAP = 2.5

        /** Overlapping covers merge unless the merged block would be more than this share of the screen. */
        const val MAX_MERGE_SCREEN_PCT = 50

        /** Moved by less than this share of its size: the same place (look-to-look jitter), not a scroll. */
        const val STILL_SHARE = 0.2

        fun merge(list: List<Pair<Cover, Px>>, screenArea: Long): List<Pair<Cover, Px>> {
            val out = list.toMutableList()
            var changed = true
            while (changed) {
                changed = false
                loop@ for (i in out.indices) {
                    for (j in i + 1 until out.size) {
                        if (inter(out[i].second, out[j].second) == 0L) continue
                        val u = union(out[i].second, out[j].second)
                        if (area(u) * 100 > screenArea * MAX_MERGE_SCREEN_PCT) continue
                        val c = mergedCover(out[i].first, out[j].first)
                        out[i] = c to u
                        out.removeAt(j)
                        changed = true
                        break@loop
                    }
                }
            }
            return out
        }

        private fun mergedCover(a: Cover, b: Cover) =
            a.copy(layer = minOf(a.layer, b.layer), concepts = (a.concepts + b.concepts).distinct().take(4))

        fun still(a: Px, b: Px): Boolean {
            val d = maxOf(
                kotlin.math.abs((a.x + a.w / 2) - (b.x + b.w / 2)),
                kotlin.math.abs((a.y + a.h / 2) - (b.y + b.h / 2))
            )
            return d <= STILL_SHARE * maxOf(a.w, a.h, b.w, b.h)
        }

        fun area(r: Px): Long = r.w.toLong() * r.h

        fun inter(a: Px, b: Px): Long {
            val w = minOf(a.x + a.w, b.x + b.w) - maxOf(a.x, b.x)
            val h = minOf(a.y + a.h, b.y + b.h) - maxOf(a.y, b.y)
            return if (w <= 0 || h <= 0) 0L else w.toLong() * h
        }

        fun overlapFrac(a: Px, b: Px): Double {
            val m = minOf(area(a), area(b))
            return if (m <= 0) 0.0 else inter(a, b).toDouble() / m
        }

        fun union(a: Px, b: Px): Px {
            val x0 = minOf(a.x, b.x)
            val y0 = minOf(a.y, b.y)
            return Px(x0, y0, maxOf(a.x + a.w, b.x + b.w) - x0, maxOf(a.y + a.h, b.y + b.h) - y0)
        }
    }
}
