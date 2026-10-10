package com.veil.guard.overlay

import android.content.Context
import android.os.SystemClock
import java.io.File

/**
 * Why a cover is there, in words the user recognises: the built-in category ("Violence & gore", "Political
 * content", "Nudity") or the word they typed. Read from the concepts folder (pack files are "<pack>--<file>.json").
 */
object CoverNames {
    private val PACK_NAMES = mapOf("politics" to "Political content", "violence" to "Violence & gore")
    private val ID = Regex("\"conceptId\"\\s*:\\s*\"([^\"]+)\"")

    @Volatile private var names: Map<String, String> = emptyMap()

    @Volatile private var builtMs = 0L

    @Volatile private var violence: Set<String> = emptySet()

    /** In [child] mode nudity and violence & gore are never named: the label is empty (icon + "Hidden" only). */
    fun reason(ctx: Context, c: Cover, child: Boolean = false): String {
        if (c.layer == 1) return if (child) "" else "Nudity"
        val ids = c.concepts.ifEmpty { return "Hidden content" }
        val map = names(ctx)
        val kept = if (child) ids.filter { it !in violence } else ids
        if (kept.isEmpty()) return ""
        return kept.map { map[it] ?: it.replace('-', ' ') }.distinct().take(2).joinToString(" · ")
    }

    private fun names(ctx: Context): Map<String, String> {
        val now = SystemClock.uptimeMillis()
        if (now - builtMs < REFRESH_MS && names.isNotEmpty()) return names
        val dir = File(ctx.externalMediaDirs.firstOrNull() ?: return names, "concepts")
        val m = HashMap<String, String>()
        val v = HashSet<String>()
        for (f in dir.listFiles { x -> x.extension == "json" }.orEmpty()) {
            val id = runCatching {
                f.bufferedReader().use { r -> CharArray(600).let { b -> String(b, 0, r.read(b).coerceAtLeast(0)) } }
            }.getOrNull()?.let { ID.find(it)?.groupValues?.get(1) } ?: continue
            val pack = f.name.substringBefore("--", "")
            if (pack == "violence") v.add(id)
            m[id] = PACK_NAMES[pack] ?: id.replace('-', ' ')
        }
        names = m
        violence = v
        builtMs = now
        return m
    }

    private const val REFRESH_MS = 5000L
}
