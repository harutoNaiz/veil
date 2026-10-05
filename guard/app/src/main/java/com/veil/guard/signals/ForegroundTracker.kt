package com.veil.guard.signals

/** Remembers the last real app. Our own package, system UI and keyboards never count as the foreground app. */
class ForegroundTracker(private val ownPackage: String = "com.veil.guard") {
    @Volatile var current: String? = null
        private set

    fun onWindowState(pkg: String?, className: String?): String? {
        if (pkg == null || pkg == ownPackage || pkg in IGNORED || pkg.contains("inputmethod")) return current
        current = pkg
        return current
    }

    companion object {
        val IGNORED =
            setOf(
                "com.android.systemui",
                "android",
                "com.google.android.inputmethod.latin",
                "com.android.inputmethod.latin",
                "com.iqoo.inputmethod",
                "com.vivo.upslide",
                "com.sohu.inputmethod.sogou",
                "com.touchtype.swiftkey"
            )
    }
}
