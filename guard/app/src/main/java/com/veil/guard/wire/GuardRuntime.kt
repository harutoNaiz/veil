package com.veil.guard.wire

import android.content.Context
import android.os.Handler
import android.os.HandlerThread
import android.os.SystemClock
import android.os.Trace
import com.veil.guard.wire.ml.ConceptWatcher
import com.veil.guard.wire.ml.LiveLanes
import java.io.File
import java.util.concurrent.atomic.AtomicBoolean

/** Process-wide runtime: one `veil-conductor` thread owning a [GuardCore]. All entry points are thread-safe. */
object GuardRuntime {
    private val DEFAULT_SKIP = setOf("com.veil.guard", "com.veil.console", "com.android.settings")
    private var thread: HandlerThread? = null
    private var handler: Handler? = null
    private var worker: ThreadWorker? = null

    @Volatile private var core: GuardCore? = null
    private const val DEBOUNCE_MS = 150L
    private val pumpQueued = AtomicBoolean(false)
    private var appCtx: Context? = null
    private var skip: Set<String> = DEFAULT_SKIP
    private var watcher: ConceptWatcher? = null

    @Synchronized
    fun start(ctx: Context) {
        if (core != null) return
        val app = ctx.applicationContext
        appCtx = app
        val params = app.assets.open("params.json").bufferedReader().use { it.readText() }
        val mode = prefs(app).getString("mode", "balanced") ?: "balanced"
        val t = HandlerThread("veil-conductor").also { it.start() }
        val h = Handler(t.looper)
        val log = JsonlDebugLog(File(app.filesDir, "debug.jsonl"))
        val w = ThreadWorker({ h.post(it) }, { schedulePump() })
        val c =
            GuardCore(
                params,
                mode,
                { LiveLanes.build(app, it) },
                w,
                { WireHub.overlay },
                { WireHub.layout() },
                log,
                skip,
                { SystemClock.uptimeMillis() },
                { name, body ->
                    Trace.beginSection(name)
                    try {
                        body()
                    } finally {
                        Trace.endSection()
                    }
                }
            )
        thread = t
        handler = h
        worker = w
        core = c
        if (mode == "off") h.post { c.pause() }
        WireHub.log = log
        WireHub.frames = { f ->
            c.offer(f)
            schedulePump()
        }
        WireHub.events = { e -> h.post { c.onEvent(e) } }
        WireHub.drawn = { t0 -> h.post { c.onDrawn(t0) } }
        val dir = File(app.externalMediaDirs.first(), "concepts").also { it.mkdirs() }
        val r = Runnable { reloadLanes() }
        watcher = ConceptWatcher(dir) {
            h.removeCallbacks(r)
            h.postDelayed(r, DEBOUNCE_MS)
        }.also { it.start() }
    }

    private fun schedulePump() {
        val h = handler ?: return
        if (pumpQueued.compareAndSet(false, true)) {
            h.post {
                pumpQueued.set(false)
                core?.pump()
            }
        }
    }

    private fun run(block: (GuardCore) -> Unit) {
        val c = core ?: return
        handler?.post { block(c) }
    }

    fun pause() = run { it.pause() }

    fun resume() = run { it.resume() }

    fun setMode(m: String) {
        appCtx?.let { prefs(it).edit().putString("mode", m).apply() }
        run { it.setMode(m) }
    }

    fun setSkipApps(pkgs: Set<String>) {
        skip = pkgs
        run { it.setSkipApps(pkgs) }
    }

    fun reloadLanes() = run {
        it.swapLanes()
        WireHub.log?.write(
            mapOf("kind" to "concepts", "tMs" to SystemClock.uptimeMillis(), "lanes" to it.buildCount)
        )
    }

    fun writeStatus(ctx: Context) {
        run { c ->
            val s = linkedMapOf("mode" to c.mode, "userPaused" to c.userPaused, "lastStats" to c.lastStats)
            runCatching {
                File(ctx.applicationContext.filesDir, "status.json").writeText(JsonlDebugLog.encode(s))
            }
        }
    }

    @Synchronized
    fun stop() {
        watcher?.stop()
        watcher = null
        WireHub.frames = null
        WireHub.events = null
        WireHub.drawn = null
        WireHub.log = null
        core = null
        worker?.shutdown()
        worker = null
        thread?.quitSafely()
        thread = null
        handler = null
    }

    private fun prefs(ctx: Context) = ctx.getSharedPreferences("veil_guard", Context.MODE_PRIVATE)
}
