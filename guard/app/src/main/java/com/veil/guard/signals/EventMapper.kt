package com.veil.guard.signals

/** Pure mapping from a copied-out [RawEvent] to a [UiEvent]. Never touches the accessibility tree. */
class EventMapper(private val scroll: ScrollNormaliser = ScrollTracker()) {
    fun map(raw: RawEvent, nextId: () -> Long): UiEvent? = when (raw.type) {
        TYPE_VIEW_SCROLLED -> mapScroll(raw, nextId)

        TYPE_WINDOW_STATE_CHANGED -> {
            val pkg = raw.packageName
            if (pkg == null) {
                null
            } else {
                WindowChanged(nextId(), raw.tMs, pkg, raw.className, raw.windowId.takeIf { it >= 0 })
            }
        }

        TYPE_WINDOW_CONTENT_CHANGED ->
            ContentChanged(
                nextId(),
                raw.tMs,
                raw.packageName,
                raw.sourceRect,
                changeTypeNames(raw.contentChangeTypes)
            )

        TYPE_WINDOWS_CHANGED -> {
            scroll.reset()
            null
        }

        else -> null
    }

    private fun mapScroll(raw: RawEvent, nextId: () -> Long): UiEvent? {
        val d = scroll.onScroll(raw) ?: return null
        return Scrolled(nextId(), raw.tMs, raw.packageName, d.dx, d.dy, d.containerRect, d.containerId)
    }

    companion object {
        const val TYPE_VIEW_SCROLLED = 0x1000
        const val TYPE_WINDOW_STATE_CHANGED = 0x20
        const val TYPE_WINDOW_CONTENT_CHANGED = 0x800
        const val TYPE_WINDOWS_CHANGED = 0x400000

        private val CHANGE_NAMES =
            listOf(
                1 to "subtree",
                2 to "text",
                4 to "contentDescription",
                8 to "paneTitle",
                16 to "paneAppeared",
                32 to "paneDisappeared",
                64 to "stateDescription",
                128 to "drawingOrder",
                256 to "error"
            )

        fun changeTypeNames(bits: Int): List<String> = CHANGE_NAMES.filter { bits and it.first != 0 }.map { it.second }
    }
}
