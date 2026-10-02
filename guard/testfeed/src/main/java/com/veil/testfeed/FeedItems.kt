package com.veil.testfeed

import java.util.Locale

data class FeedItem(val id: String, val kind: String, val heightDp: Int, val color: Int, val label: String)

/** The fixed list of feed items shown by the Test Feed. Deterministic: the same every run. */
object FeedItems {
    val KINDS = listOf("clean", "cat", "clean", "spider", "lookalike", "clean", "ruler", "repost")

    const val COUNT = 60
    const val REPOST_OF = "item-001"
    private const val RULER_HEIGHT_DP = 480
    private const val DEFAULT_HEIGHT_DP = 320

    private val COLORS =
        mapOf(
            "clean" to 0xFFECEFF1.toInt(),
            "cat" to 0xFFFFCC80.toInt(),
            "spider" to 0xFFB39DDB.toInt(),
            "lookalike" to 0xFFA5D6A7.toInt(),
            "ruler" to 0xFFFFFFFF.toInt(),
            "repost" to 0xFFFFCC80.toInt()
        )

    /**
     * 60 items, i = 0..59: id "item-%03d", kind KINDS[i % 8], heightDp 480 for "ruler" else 320, colour by kind,
     * label "#%03d <kind>" (+ " of item-001" for repost).
     */
    fun defaultFeed(): List<FeedItem> = List(COUNT) { i ->
        val kind = KINDS[i % KINDS.size]
        val suffix = if (kind == "repost") " of $REPOST_OF" else ""
        FeedItem(
            id = String.format(Locale.ROOT, "item-%03d", i),
            kind = kind,
            heightDp = if (kind == "ruler") RULER_HEIGHT_DP else DEFAULT_HEIGHT_DP,
            color = COLORS.getValue(kind),
            label = String.format(Locale.ROOT, "#%03d %s", i, kind) + suffix
        )
    }
}
