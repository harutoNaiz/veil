package com.veil.guard.overlay

/** Pure rules for how a cover is labelled: which icon, which calm wording. */
object CoverLook {
    /** Category of a cover from its layer and the pack of each concept ("" or null = a user word). */
    fun category(layer: Int, packs: List<String?>): String {
        if (layer == 1) return "nudity"
        val kinds = packs.map { if (it == "politics" || it == "violence" || it == "sexual") it else "word" }.toSet()
        return kinds.singleOrNull() ?: "mixed"
    }

    /** Icon to draw: child mode never hints at nudity, sexual content or violence. */
    fun icon(category: String, child: Boolean): String = when (category) {
        "nudity", "sexual" -> if (child) "eye" else "heart"
        "violence" -> if (child) "eye" else "drop"
        "politics" -> "flag"
        "word" -> "tag"
        else -> "eye"
    }

    /** Head and second line. [reveal] = adult mode with Continue; [child] = parental control. */
    fun texts(reason: String, reveal: Boolean, child: Boolean): Pair<String, String> = when {
        child -> "Hidden for you" to reason.ifEmpty { "Not for kids" }

        reveal -> {
            val why = reason.replace(" · ", ", ").lowercase()
            val line = if (why.isEmpty() || why == "hidden content") "" else "May contain $why"
            "Sensitive content" to line
        }

        else -> "Hidden" to reason
    }

    /** A cover is "big" (likely a video) when it fills at least a fifth of the screen. */
    fun isBig(area: Long, screenArea: Long): Boolean = screenArea > 0 && area * 5 >= screenArea
}
