package com.veil.guard.overlay.blind

/** Pure state machine: when to show the "can't see this app" chip. */
class BlindHintPolicy(private val debounceMs: Long = 2000L) {
    private var pkg: String? = null
    private var blindSince: Long? = null
    private val dismissed = HashSet<String>()

    var visible: Boolean = false
        private set

    /** Feed one frame verdict for the foreground app; returns whether the chip should show. */
    fun onFrame(pkg: String?, blind: Boolean, nowMs: Long): Boolean {
        if (pkg != this.pkg) {
            this.pkg = pkg
            blindSince = null
            visible = false
        }
        if (pkg == null || !blind || pkg in dismissed) {
            blindSince = null
            visible = false
            return false
        }
        val since = blindSince ?: nowMs.also { blindSince = it }
        if (nowMs - since >= debounceMs) visible = true
        return visible
    }

    /** User closed the chip: never show again for this app. */
    fun dismiss() {
        pkg?.let { dismissed.add(it) }
        visible = false
        blindSince = null
    }
}
