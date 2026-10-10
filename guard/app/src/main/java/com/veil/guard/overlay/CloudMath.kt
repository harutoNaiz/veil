package com.veil.guard.overlay

import kotlin.math.ceil
import kotlin.math.hypot
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt
import kotlin.math.sin

/** One captured frame as the cover painter sees it (ARGB at capture resolution). */
class FrameSnapshot(val id: Long, val argb: IntArray, val w: Int, val h: Int, val screenW: Int, val screenH: Int)

/** The painter pulls pixels from here; null = no usable frame, draw the pixel-free frosted cloud. */
fun interface FrameSampleSource {
    /** [rect] and [dispW]/[dispH] are display pixels. Must return null if the frame may contain Veil's own covers there. */
    fun snapshot(rect: Px, dispW: Int, dispH: Int): FrameSnapshot?
}

/** Pure maths for the frosted-cloud cover: rect mapping, grid sampling, cloud-shaped alpha, compositing. */
object CloudMath {
    /** Display-pixel rect to frame-pixel rect (clamped to the frame); null if empty. */
    fun toFrame(r: Px, dispW: Int, dispH: Int, fw: Int, fh: Int): Px? {
        if (dispW <= 0 || dispH <= 0 || fw <= 0 || fh <= 0) return null
        val x0 = Math.floor(r.x.toDouble() * fw / dispW).toInt().coerceIn(0, fw)
        val y0 = Math.floor(r.y.toDouble() * fh / dispH).toInt().coerceIn(0, fh)
        val x1 = Math.ceil((r.x + r.w).toDouble() * fw / dispW).toInt().coerceIn(0, fw)
        val y1 = Math.ceil((r.y + r.h).toDouble() * fh / dispH).toInt().coerceIn(0, fh)
        return if (x1 > x0 && y1 > y0) Px(x0, y0, x1 - x0, y1 - y0) else null
    }

    /** True if the frame can show our own covers over [rect] (same coordinate space for both). */
    fun overlapsOwn(rect: Px, own: List<Px>): Boolean = own.any {
        it.x < rect.x + rect.w && rect.x < it.x + it.w && it.y < rect.y + rect.h && rect.y < it.y + it.h
    }

    /**
     * Can a frame be used as the cover's pixel source? Window screenshots never contain our covers; display
     * mirrors (MediaProjection) do, so they only qualify where no own cover sat when captured.
     */
    fun frameUsable(sourceHasOwnCovers: Boolean, rectScreen: Px, ownAtCapture: List<Px>): Boolean =
        !sourceHasOwnCovers || !overlapsOwn(rectScreen, ownAtCapture)

    /** Texel grid for a cover: long side at most [maxTexels], so at most that much detail survives. */
    fun gridSize(w: Int, h: Int, density: Float, maxTexels: Int): Pair<Int, Int> {
        val long = max(w, h).coerceAtLeast(1)
        val short = min(w, h).coerceAtLeast(1)
        val n = ceil(long / (60.0 * density)).toInt().coerceIn(2, maxTexels)
        val m = (n.toDouble() * short / long).roundToInt().coerceIn(2, n)
        return if (w >= h) n to m else m to n
    }

    /** Box-averaged colours of [src] (frame pixels) on a gw x gh grid, then smoothed. */
    fun sampleGrid(argb: IntArray, fw: Int, fh: Int, src: Px, gw: Int, gh: Int): IntArray {
        val out = IntArray(gw * gh)
        for (gy in 0 until gh) {
            val y0 = src.y + src.h * gy / gh
            val y1 = max(y0 + 1, src.y + src.h * (gy + 1) / gh)
            val sy = max(1, (y1 - y0) / 6)
            for (gx in 0 until gw) {
                val x0 = src.x + src.w * gx / gw
                val x1 = max(x0 + 1, src.x + src.w * (gx + 1) / gw)
                val sx = max(1, (x1 - x0) / 6)
                var r = 0L
                var g = 0L
                var b = 0L
                var n = 0
                var y = y0
                while (y < y1) {
                    val row = min(y, fh - 1) * fw
                    var x = x0
                    while (x < x1) {
                        val c = argb[row + min(x, fw - 1)]
                        r += c shr 16 and 0xFF
                        g += c shr 8 and 0xFF
                        b += c and 0xFF
                        n++
                        x += sx
                    }
                    y += sy
                }
                out[gy * gw + gx] =
                    if (n == 0) 0xFF808080.toInt() else pack((r / n).toInt(), (g / n).toInt(), (b / n).toInt())
            }
        }
        return smooth(smooth(out, gw, gh), gw, gh)
    }

    /** 3x3 box blur with clamped edges. */
    fun smooth(g: IntArray, gw: Int, gh: Int): IntArray {
        val out = IntArray(g.size)
        for (y in 0 until gh) {
            for (x in 0 until gw) {
                var r = 0
                var gg = 0
                var b = 0
                var n = 0
                for (dy in -1..1) {
                    for (dx in -1..1) {
                        val c = g[(y + dy).coerceIn(0, gh - 1) * gw + (x + dx).coerceIn(0, gw - 1)]
                        r += c shr 16 and 0xFF
                        gg += c shr 8 and 0xFF
                        b += c and 0xFF
                        n++
                    }
                }
                out[y * gw + x] = pack(r / n, gg / n, b / n)
            }
        }
        return out
    }

    /** Pixel-free fallback: soft diagonal gradient with a lighter lobe, tinted for light or dark pages. */
    fun fallbackGrid(gw: Int, gh: Int, night: Boolean): IntArray {
        val lo = if (night) 0x2B2F36 else 0xCDD3DC
        val hi = if (night) 0x454B55 else 0xEEF1F6
        return IntArray(gw * gh) { i ->
            val x = (i % gw + 0.5) / gw
            val y = (i / gw + 0.5) / gh
            val t = (0.55 * (1 - x) + 0.45 * (1 - y) + 0.25 * sin(x * 3.1 + y * 2.3)).coerceIn(0.0, 1.0)
            mix(0xFF000000.toInt() or lo, 0xFF000000.toInt() or hi, t.toFloat())
        }
    }

    /** Feather margin around the rect, in px. */
    fun margin(w: Int, h: Int, density: Float): Float = (min(w, h) * 0.2f).coerceIn(4f * density, 18f * density)

    /**
     * Cloud alpha at cover-local (x, y) for a w x h rect: 1 on the rect, fading over a lobed distance
     * (0.55..1.0 x margin) outside it, so the edge is a puffy cloud rather than a rectangle.
     */
    fun alpha(x: Float, y: Float, w: Int, h: Int, margin: Float, seed: Int): Float {
        val dx = max(max(-x, x - w), 0f)
        val dy = max(max(-y, y - h), 0f)
        if (dx == 0f && dy == 0f) return 1f
        val d = hypot(dx, dy)
        val lam = max(margin * 1.6f, 14f)
        val s = seed * 1.7f
        val lobe = (sin(x / lam + s) + sin(y / lam * 1.3f + s * 0.7f) + sin((x + y) / lam * 0.7f + s * 1.3f)) / 3f
        val limit = margin * (0.775f + 0.225f * lobe) // 0.55..1.0
        val t = (d / limit).coerceIn(0f, 1f)
        val sm = t * t * (3 - 2 * t)
        return 1f - sm
    }

    /**
     * Final ARGB (straight alpha) of the cloud over [w]+2m by [h]+2m px at ow x oh texels. Grid colours are
     * upsampled bilinearly, pushed toward a light or dark frost (by local luma) and lightly modulated by cloud noise.
     */
    fun compose(
        grid: IntArray,
        gw: Int,
        gh: Int,
        w: Int,
        h: Int,
        margin: Float,
        ow: Int,
        oh: Int,
        frost: Float,
        coreAlpha: Float,
        seed: Int
    ): IntArray {
        val out = IntArray(ow * oh)
        val tw = w + 2 * margin
        val th = h + 2 * margin
        // One frost tint per cloud (from its mean luma), so dark shapes are lifted, not deepened into silhouettes.
        val f = if (meanLuma(grid) >= 110) 0xFFEEF1F5.toInt() else 0xFF2A2E35.toInt()
        for (j in 0 until oh) {
            for (i in 0 until ow) {
                val x = (i + 0.5f) / ow * tw - margin
                val y = (j + 0.5f) / oh * th - margin
                val a = alpha(x, y, w, h, margin, seed) * coreAlpha
                if (a <= 0.003f) continue
                val base = bilinear(grid, gw, gh, (x / w).coerceIn(0f, 1f), (y / h).coerceIn(0f, 1f))
                val c = mix(base, f, frost)
                out[j * ow + i] = (min(255, (a * 255f).roundToInt()) shl 24) or (c and 0xFFFFFF)
            }
        }
        return out
    }

    /**
     * "Sensitive content" veil: the cover's own colours, smoothed bilinearly from the coarse grid (no shapes survive),
     * evenly dimmed toward [dimTo] by [dim]. Opaque, uniform, exactly ow x oh (drawn inside the cover rect only).
     */
    fun veil(grid: IntArray, gw: Int, gh: Int, ow: Int, oh: Int, dimTo: Int, dim: Float): IntArray =
        IntArray(ow * oh) { k ->
            val u = ((k % ow) + 0.5f) / ow
            val v = ((k / ow) + 0.5f) / oh
            mix(bilinear(grid, gw, gh, u, v), dimTo, dim)
        }

    fun meanLuma(g: IntArray): Int {
        if (g.isEmpty()) return 128
        var s = 0L
        for (c in g) s += ((c shr 16 and 0xFF) * 77 + (c shr 8 and 0xFF) * 150 + (c and 0xFF) * 29) shr 8
        return (s / g.size).toInt()
    }

    private fun bilinear(g: IntArray, gw: Int, gh: Int, u: Float, v: Float): Int {
        val fx = (u * gw - 0.5f).coerceIn(0f, (gw - 1).toFloat())
        val fy = (v * gh - 0.5f).coerceIn(0f, (gh - 1).toFloat())
        val x0 = fx.toInt()
        val y0 = fy.toInt()
        val x1 = min(gw - 1, x0 + 1)
        val y1 = min(gh - 1, y0 + 1)
        val tx = fx - x0
        val ty = fy - y0
        val top = mix(g[y0 * gw + x0], g[y0 * gw + x1], tx)
        val bot = mix(g[y1 * gw + x0], g[y1 * gw + x1], tx)
        return mix(top, bot, ty)
    }

    fun mix(a: Int, b: Int, t: Float): Int {
        fun ch(s: Int) =
            ((a shr s and 0xFF) + ((b shr s and 0xFF) - (a shr s and 0xFF)) * t).roundToInt().coerceIn(0, 255)
        return pack(ch(16), ch(8), ch(0))
    }

    private fun pack(r: Int, g: Int, b: Int) = (0xFF shl 24) or (r shl 16) or (g shl 8) or b
}
