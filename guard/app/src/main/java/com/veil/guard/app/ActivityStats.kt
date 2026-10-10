package com.veil.guard.app

import android.content.Context
import android.os.SystemClock
import com.veil.guard.overlay.Cover
import com.veil.guard.overlay.Px
import java.io.File
import java.time.LocalDate
import java.util.concurrent.Executors

/** Totals for one day. Counts only: no images, text or timestamps finer than the day are ever kept. */
data class DaySummary(val day: String, val byCategory: Map<String, Int>, val byApp: Map<String, Int>) {
    val total get() = byCategory.values.sum()
}

/** Pure helpers (JVM-testable): key layout, aggregation, pruning. */
object StatsCore {
    val CATEGORIES = listOf("nudity", "sexual", "violence", "politics", "word")

    fun catKey(day: String, cat: String) = "d:$day:c:$cat"

    fun appKey(day: String, pkg: String) = "d:$day:a:$pkg"

    fun summarize(all: Map<String, Int>, day: String): DaySummary {
        val cats = HashMap<String, Int>()
        val apps = HashMap<String, Int>()
        val cp = "d:$day:c:"
        val ap = "d:$day:a:"
        for ((k, v) in all) {
            if (k.startsWith(cp)) cats[k.substring(cp.length)] = v
            if (k.startsWith(ap)) apps[k.substring(ap.length)] = v
        }
        return DaySummary(day, cats, apps)
    }

    /** [n] days ending at [today], oldest first. */
    fun lastDays(today: LocalDate, n: Int): List<String> =
        (n - 1 downTo 0).map { today.minusDays(it.toLong()).toString() }

    /** Keys whose day is not in [keep]. */
    fun stale(keys: Collection<String>, keep: Set<String>): List<String> =
        keys.filter { k -> k.startsWith("d:") && k.substring(2, minOf(12, k.length)) !in keep }

    fun topApps(s: DaySummary, n: Int): List<Pair<String, Int>> =
        s.byApp.entries.sortedByDescending { it.value }.take(n).map { it.key to it.value }
}

/** Decides which covers in a stream of plans are new (not the same cover seen a moment ago, even if scrolled). */
class NewCoverTracker(private val ttlMs: Long = 2000) {
    private class Seen(var x: Int, var y: Int, var w: Int, var h: Int, var last: Long)

    private val seen = ArrayList<Seen>()

    fun newOnes(rects: List<Px>, now: Long): List<Int> {
        seen.removeAll { now - it.last > ttlMs }
        val used = HashSet<Seen>()
        val out = ArrayList<Int>()
        val fresh = ArrayList<Seen>()
        rects.forEachIndexed { i, r ->
            val m = seen.firstOrNull { it !in used && same(it, r) }
            if (m == null) {
                out.add(i)
                fresh.add(Seen(r.x, r.y, r.w, r.h, now))
            } else {
                m.x = r.x
                m.y = r.y
                m.w = r.w
                m.h = r.h
                m.last = now
                used.add(m)
            }
        }
        seen.addAll(fresh)
        return out
    }

    private fun same(s: Seen, r: Px): Boolean {
        val ix = minOf(s.x + s.w, r.x + r.w) - maxOf(s.x, r.x)
        val iy = minOf(s.y + s.h, r.y + r.h) - maxOf(s.y, r.y)
        val inter = if (ix > 0 && iy > 0) ix.toLong() * iy else 0L
        val smaller = minOf(s.w.toLong() * s.h, r.w.toLong() * r.h).coerceAtLeast(1)
        if (inter * 2 >= smaller) return true
        // Same size and still close in x: the content scrolled.
        return close(s.w, r.w) && close(s.h, r.h) && kotlin.math.abs(s.x - r.x) <= s.w / 4 + 1
    }

    private fun close(a: Int, b: Int) = kotlin.math.abs(a - b) <= maxOf(a, b) / 10 + 1
}

/** On-device daily counters ("veil_stats"): hidden items per category and per app, last 14 days. */
object ActivityStats {
    private const val PREFS = "veil_stats"
    private const val KEEP_DAYS = 14
    private val io = Executors.newSingleThreadExecutor { r -> Thread(r, "veil-stats").apply { isDaemon = true } }
    private val tracker = NewCoverTracker()
    private val ID = Regex("\"conceptId\"\\s*:\\s*\"([^\"]+)\"")
    private var packOf: Map<String, String> = emptyMap()
    private var builtMs = 0L

    /** Main thread: called with every plan's covers (display pixels); counts the ones that just appeared. */
    fun observe(ctx: Context, targets: List<Pair<Cover, Px>>) {
        val fresh = tracker.newOnes(targets.map { it.second }, SystemClock.uptimeMillis()).map { targets[it].first }
        if (fresh.isEmpty()) return
        val pkg = com.veil.guard.signals.SignalsHub.foregroundPackage ?: "unknown"
        val app = ctx.applicationContext
        io.execute { runCatching { fresh.forEach { record(app, category(app, it), pkg) } } }
    }

    fun record(ctx: Context, category: String, pkg: String) {
        val p = ctx.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        synchronized(this) {
            val today = LocalDate.now().toString()
            val e = p.edit()
            for (k in listOf(StatsCore.catKey(today, category), StatsCore.appKey(today, pkg))) {
                e.putInt(k, p.getInt(k, 0) + 1)
            }
            val keep = StatsCore.lastDays(LocalDate.now(), KEEP_DAYS).toSet()
            StatsCore.stale(p.all.keys, keep).forEach { e.remove(it) }
            e.apply()
        }
    }

    fun today(ctx: Context): DaySummary = last7Days(ctx).last()

    /** Oldest first, today last. */
    fun last7Days(ctx: Context): List<DaySummary> {
        val all = ctx.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE).all
            .mapNotNull { (k, v) -> (v as? Int)?.let { k to it } }.toMap()
        return StatsCore.lastDays(LocalDate.now(), 7).map { StatsCore.summarize(all, it) }
    }

    /** nudity for layer 1; the pack a concept belongs to (politics, violence, sexual); otherwise a typed word. */
    fun category(ctx: Context, c: Cover): String {
        if (c.layer == 1) return "nudity"
        val map = packs(ctx)
        return c.concepts.firstNotNullOfOrNull { map[it] } ?: "word"
    }

    private fun packs(ctx: Context): Map<String, String> {
        val now = SystemClock.uptimeMillis()
        if (now - builtMs < 5000 && packOf.isNotEmpty()) return packOf
        val dir = File(ctx.externalMediaDirs.firstOrNull() ?: return packOf, "concepts")
        val m = HashMap<String, String>()
        for (f in dir.listFiles { x -> x.extension == "json" }.orEmpty()) {
            val pack = f.name.substringBefore("--", "")
            if (pack != "politics" && pack != "violence" && pack != "sexual") continue
            val id = runCatching {
                f.bufferedReader().use { r -> CharArray(600).let { b -> String(b, 0, r.read(b).coerceAtLeast(0)) } }
            }.getOrNull()?.let { ID.find(it)?.groupValues?.get(1) } ?: continue
            m[id] = pack
        }
        packOf = m
        builtMs = now
        return m
    }
}
