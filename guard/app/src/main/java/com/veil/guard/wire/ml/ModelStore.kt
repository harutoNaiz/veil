package com.veil.guard.wire.ml

import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import android.content.Context
import com.veil.guard.wire.WireHub
import com.veil.guard.wire.ml.accel.Accel
import java.io.File

/**
 * ONNX sessions from <externalMedia>/models. Vision models run on QNN/HTP when supported (override: <models>/accel =
 * cpu|xnnpack|qnn), but a QNN compile can take minutes, so [session] never waits for one: it returns the QNN session
 * when already compiled (context cache) or ready, else a CPU session. [warmUp] compiles the QNN sessions on a
 * background thread; callers then pick them up with [ready]. Any accelerator failure falls back to CPU with a warn log.
 */
class ModelStore(
    private val ctx: Context,
    private val mode: Accel.Mode? = null,
    private val threads: Int = Accel.defaultThreads()
) {
    val env: OrtEnvironment = Accel.prepareProcess(ctx).let { OrtEnvironment.getEnvironment() }

    val dir: File get() = File(ctx.externalMediaDirs.first(), "models")

    private val qnnDir: File get() = Accel.qnnDir(ctx)

    /** Provider in force for the vision models. */
    val activeMode: Accel.Mode get() = mode ?: Accel.modeFor(ctx, dir)

    /** SigLIP2 batch sizes worth loading: the b16 graph costs ~13 min to compile on the HTP and b4 x N is as fast. */
    fun imageBatches(): List<Int> = if (activeMode == Accel.Mode.QNN) listOf(1, 4) else listOf(1, 4, 16)

    fun session(name: String): OrtSession? {
        val m = activeMode
        return open(env, dir, name, m, threads, qnnDir)
    }

    fun has(name: String): Boolean = File(dir, name).isFile

    /** Provider the session for name last handed out runs on ("cpu", "xnnpack", "qnn-htp"), null if never opened. */
    fun ep(name: String): String? = epOf(name)

    /** The compiled QNN session for name once ready, else null (callers keep the CPU session meanwhile). */
    fun ready(name: String): OrtSession? = qnnReady(File(dir, name))

    /** Ready QNN sessions for the image batches, or null until all of them are ready. */
    fun readyImage(): Map<Int, OrtSession>? {
        val out = HashMap<Int, OrtSession>()
        for (b in imageBatches()) {
            if (!has("siglip2-image-b$b.onnx")) continue
            out[b] = ready("siglip2-image-b$b.onnx") ?: return null
        }
        return out.ifEmpty { null }
    }

    /**
     * Compile the QNN sessions of the vision models in the background (one thread, in priority order), logging each
     * session and a final accel-ready line. No-op unless the mode is QNN; already-ready or earlier-failed models are skipped.
     */
    fun warmUp(names: List<String> = DEFAULT_WARM) {
        if (activeMode != Accel.Mode.QNN) return
        startWarm(env, dir, names, threads, qnnDir)
    }

    companion object {
        val DEFAULT_WARM = listOf(
            "nudenet-320n.onnx",
            "siglip2-image-b1.onnx",
            "siglip2-image-b4.onnx",
            "nudenet-640m.onnx",
            "yoloe-26s-embed-top100.onnx"
        )

        private val cache = HashMap<String, Triple<Long, OrtSession, String>>() // cpu/xnnpack sessions
        private val qnn = HashMap<String, Pair<Long, OrtSession>>() // ready QNN sessions by file name
        private val eps = HashMap<String, String>()
        private val inflight = HashSet<String>()

        private fun stamp(f: File) = f.lastModified() xor f.length()

        @Synchronized
        private fun epOf(name: String): String? = eps[name]

        @Synchronized
        private fun qnnReady(f: File): OrtSession? = qnn[f.name]?.takeIf { it.first == stamp(f) }?.second

        @Synchronized
        private fun markReady(n: String, f: File, o: Accel.Opened) {
            qnn[n] = stamp(f) to o.session
            eps[n] = o.ep
        }

        @Synchronized
        private fun done(n: String) {
            inflight -= n
        }

        private fun logSession(name: String, o: Accel.Opened, wanted: String, threads: Int, ms: Long) {
            WireHub.log?.write(
                mapOf(
                    "kind" to "info",
                    "what" to "session",
                    "model" to name,
                    "ep" to o.ep,
                    "wanted" to wanted,
                    "threads" to threads,
                    "cachedCtx" to o.cached,
                    "loadMs" to ms
                )
            )
        }

        @Synchronized
        private fun open(
            env: OrtEnvironment,
            dir: File,
            name: String,
            wanted: Accel.Mode,
            threads: Int,
            qnnDir: File
        ): OrtSession? {
            val f = File(dir, name)
            if (!f.isFile) {
                WireHub.log?.write(mapOf("kind" to "warn", "what" to "model-missing", "file" to name))
                return null
            }
            var mode = if (Accel.accelerable(name)) wanted else Accel.Mode.CPU
            if (mode == Accel.Mode.QNN) {
                qnnReady(f)?.let {
                    eps[name] = "qnn-htp"
                    return it
                }
                // Only a compiled context loads fast enough to wait for; otherwise CPU now, QNN via warmUp.
                if (Accel.hasCtx(f, qnnDir) && !Accel.qnnFailedBefore(f, qnnDir)) {
                    val t0 = System.nanoTime()
                    try {
                        val o = Accel.openQnn(env, f, threads, qnnDir)
                        qnn[name] = stamp(f) to o.session
                        eps[name] = o.ep
                        logSession(name, o, "qnn", threads, (System.nanoTime() - t0) / 1_000_000)
                        return o.session
                    } catch (t: Throwable) {
                        Accel.warn("ep-fallback", t, mapOf("model" to name, "wanted" to "qnn", "using" to "cpu"))
                    }
                }
                mode = Accel.Mode.CPU
            }
            val key = "$name|${mode.wire}|$threads"
            cache[key]?.let { (st, s, ep) ->
                if (st == stamp(f)) {
                    eps[name] = ep
                    return s
                }
                runCatching { s.close() }
            }
            val t0 = System.nanoTime()
            val o = Accel.open(env, f, mode, threads, null)
            cache[key] = Triple(stamp(f), o.session, o.ep)
            eps[name] = o.ep
            logSession(name, o, mode.wire, threads, (System.nanoTime() - t0) / 1_000_000)
            return o.session
        }

        @Synchronized
        private fun startWarm(env: OrtEnvironment, dir: File, names: List<String>, threads: Int, qnnDir: File) {
            val todo = names.filter { n ->
                val f = File(dir, n)
                f.isFile && Accel.accelerable(n) && qnnReady(f) == null && n !in inflight &&
                    !Accel.qnnFailedBefore(f, qnnDir)
            }
            if (todo.isEmpty()) return
            inflight += todo
            Thread({
                val t0 = System.nanoTime()
                val ok = ArrayList<String>()
                val bad = ArrayList<String>()
                for (n in todo) {
                    val f = File(dir, n)
                    val s0 = System.nanoTime()
                    try {
                        val o = Accel.openQnn(env, f, threads, qnnDir)
                        markReady(n, f, o)
                        logSession(n, o, "qnn", threads, (System.nanoTime() - s0) / 1_000_000)
                        ok += n
                    } catch (t: Throwable) {
                        Accel.warn("ep-fallback", t, mapOf("model" to n, "wanted" to "qnn", "using" to "cpu"))
                        bad += n
                    }
                    done(n)
                }
                WireHub.log?.write(
                    mapOf(
                        "kind" to "info",
                        "what" to "accel-ready",
                        "ready" to ok.joinToString(","),
                        "cpuOnly" to bad.joinToString(","),
                        "totalMs" to (System.nanoTime() - t0) / 1_000_000
                    )
                )
            }, "veil-qnn-warm").apply {
                isDaemon = true
                priority = Thread.MIN_PRIORITY
            }.start()
        }
    }
}
