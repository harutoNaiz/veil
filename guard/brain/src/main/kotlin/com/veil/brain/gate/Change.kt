package com.veil.brain.gate

import com.veil.brain.contract.FrameMeta
import com.veil.brain.contract.Rect

const val THUMB_W = 32
const val THUMB_H = 64
const val TILE = 8
private const val COLS = THUMB_W / TILE
private const val ROWS = THUMB_H / TILE

data class ChangeParams(
    val ignoreTopRows: Int = 2,
    val ignoreBottomRows: Int = 2,
    val tileLevel: Int = 12,
    val cutTileLevel: Int = 40,
    val cutPct: Int = 60,
    val cutGlobal: Int = 30,
    val cutMinTiles: Int = 8
)

class ChangeResult(
    val tileScores: List<Int>,
    val changedTiles: Int,
    val sceneCut: Boolean,
    val score: Int,
    val revealedRows: Pair<Int, Int>?,
    val changedBox: IntArray?,
    val shiftRows: Int
)

object Change {
    fun shiftRows(dyScreen: Int, width: Int, height: Int, screenWidth: Int): Int {
        val num = dyScreen.toLong() * width * THUMB_H
        val den = screenWidth.toLong() * height
        val mag = ((2 * Math.abs(num) + den) / (2 * den)).toInt()
        return if (num < 0) -mag else mag
    }

    fun detect(cur: ByteArray, ref: ByteArray?, dyRows: Int, p: ChangeParams = ChangeParams()): ChangeResult {
        if (ref == null) {
            val box = intArrayOf(0, 0, THUMB_W, THUMB_H)
            return ChangeResult(List(ROWS * COLS) { 255 }, ROWS * COLS, false, 0, null, box, 0)
        }
        val top = p.ignoreTopRows
        val bot = THUMB_H - p.ignoreBottomRows
        val rev: Pair<Int, Int>? = when {
            dyRows >= bot - top || -dyRows >= bot - top -> Pair(top, bot)
            dyRows > 0 -> Pair(top, top + dyRows)
            dyRows < 0 -> Pair(bot + dyRows, bot)
            else -> null
        }
        val diff = IntArray(THUMB_H * THUMB_W)
        val lo = maxOf(top, top + dyRows)
        val hi = minOf(bot, bot + dyRows)
        for (y in lo until hi) {
            for (x in 0 until THUMB_W) {
                val c = cur[y * THUMB_W + x].toInt() and 0xFF
                val r = ref[(y - dyRows) * THUMB_W + x].toInt() and 0xFF
                diff[y * THUMB_W + x] = Math.abs(c - r)
            }
        }
        val scores = ArrayList<Int>()
        var compared = 0
        var large = 0
        var totSum = 0L
        var totN = 0L
        for (tr in 0 until ROWS) {
            val y0 = maxOf(tr * TILE, top)
            val y1 = minOf(tr * TILE + TILE, bot)
            for (tc in 0 until COLS) {
                val n = if (y1 > y0) (y1 - y0) * TILE else 0
                if (n == 0) {
                    scores.add(0)
                    continue
                }
                if (rev != null && y0 < rev.second && y1 > rev.first) {
                    scores.add(255)
                    continue
                }
                var s = 0L
                for (y in y0 until y1) for (x in tc * TILE until tc * TILE + TILE) s += diff[y * THUMB_W + x]
                val sc = (s / n).toInt()
                scores.add(sc)
                compared++
                totSum += s
                totN += n
                if (sc >= p.cutTileLevel) large++
            }
        }
        val score = if (totN > 0) (totSum / totN).toInt() else 0
        val changed = scores.indices.filter { scores[it] >= p.tileLevel }
        var box: IntArray? = null
        if (changed.isNotEmpty()) {
            val rows = changed.map { it / COLS }
            val cols = changed.map { it % COLS }
            box = intArrayOf(cols.min() * TILE, rows.min() * TILE, (cols.max() + 1) * TILE, (rows.max() + 1) * TILE)
        }
        val cut = compared >= p.cutMinTiles && large * 100 >= p.cutPct * compared && score >= p.cutGlobal
        return ChangeResult(scores, changed.size, cut, score, rev, box, dyRows)
    }

    fun thumbBoxToScreen(box: IntArray, frame: FrameMeta): Rect {
        val sw = frame.screenWidth.toLong()
        val w = frame.width.toLong()
        val h = frame.height.toLong()
        val sh = h * sw / w
        val sx0 = minOf(box[0] * sw / THUMB_W, sw)
        val sx1 = minOf(box[2] * sw / THUMB_W, sw)
        val sy0 = minOf(box[1] * h * sw / (THUMB_H * w), sh)
        val sy1 = minOf(box[3] * h * sw / (THUMB_H * w), sh)
        return Rect(sx0.toInt(), sy0.toInt(), (sx1 - sx0).toInt(), (sy1 - sy0).toInt())
    }
}
