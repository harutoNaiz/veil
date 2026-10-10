package com.veil.guard.wire.ml.accel

import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import android.content.Context
import android.system.Os
import com.veil.guard.wire.WireHub
import java.io.File

/** Execution-provider selection for the vision models (SigLIP2 image tower, NudeNet, YOLOE). Text models stay on CPU. */
object Accel {
    enum class Mode(val wire: String) {
        CPU("cpu"),
        XNNPACK("xnnpack"),
        QNN("qnn");

        companion object {
            fun parse(s: String?): Mode? = entries.firstOrNull { it.wire == s?.trim()?.lowercase() }
        }
    }

    /** A created session, the provider it really runs on (after any fallback), and whether a compiled QNN context was reused. */
    class Opened(val session: OrtSession, val ep: String, val cached: Boolean = false)

    /**
     * Bump when ORT / QNN versions change: compiled contexts are tied to them. Together with the model file stamp
     * (mtime xor size) this names the context file, so a new model file or new runtime simply recompiles.
     */
    const val CTX_TAG = "ort1.29-qnn2.42"

    /** Only the vision models are worth sending to the NPU / XNNPACK (the text model has int64 inputs). */
    fun accelerable(name: String): Boolean =
        name.startsWith("siglip2-image") || name.startsWith("nudenet") || name.startsWith("yoloe")

    fun defaultThreads(): Int = Runtime.getRuntime().availableProcessors().coerceIn(2, 6)

    /** Compiled QNN contexts live in filesDir (survive cache clearing and app updates; removed on uninstall / clear data). */
    fun qnnDir(ctx: Context): File = File(ctx.filesDir, "qnn")

    /** The HTP backend library shipped in the APK (extracted because of useLegacyPackaging). */
    fun qnnSupported(ctx: Context): Boolean = File(ctx.applicationInfo.nativeLibraryDir, "libQnnHtp.so").isFile

    /**
     * `<models>/accel` holds cpu|xnnpack|qnn to force a provider. Absent or "auto" means QNN when the HTP backend lib
     * is present, otherwise cpu (an EP that fails to load or compile still falls back to cpu per session).
     */
    fun modeFor(ctx: Context, modelsDir: File): Mode =
        Mode.parse(runCatching { File(modelsDir, "accel").readText() }.getOrNull())
            ?: if (qnnSupported(ctx)) Mode.QNN else Mode.CPU

    private var envReady = false

    /** HTP skel libs are found through ADSP_LIBRARY_PATH; must be set before the first OrtEnvironment. */
    @Synchronized
    fun prepareProcess(ctx: Context) {
        if (envReady) return
        envReady = true
        runCatching { Os.setenv("ADSP_LIBRARY_PATH", ctx.applicationInfo.nativeLibraryDir, true) }
            .onFailure { warn("adsp-path", it) }
    }

    fun warn(what: String, t: Throwable?, extra: Map<String, Any?> = emptyMap()) {
        WireHub.log?.write(
            mapOf("kind" to "warn", "what" to what, "err" to (t?.let { "${it.javaClass.simpleName}: ${it.message}" })) +
                extra
        )
    }

    private fun base(threads: Int): OrtSession.SessionOptions = OrtSession.SessionOptions().apply {
        setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT)
        setMemoryPatternOptimization(true)
        setCPUArenaAllocator(true)
        setInterOpNumThreads(1)
        setIntraOpNumThreads(threads)
    }

    /** Compiled-context file for a model. */
    fun ctxFile(file: File, cacheDir: File): File {
        val stamp = java.lang.Long.toHexString(file.lastModified() xor file.length())
        return File(cacheDir, file.name.removeSuffix(".onnx") + "_" + stamp + "_" + CTX_TAG + "_ctx.onnx")
    }

    fun hasCtx(file: File, cacheDir: File): Boolean = ctxFile(file, cacheDir).let { it.isFile && it.length() > 0 }

    private fun failedMark(file: File, cacheDir: File) = File(ctxFile(file, cacheDir).path + ".failed")

    fun qnnFailedBefore(file: File, cacheDir: File): Boolean = failedMark(file, cacheDir).exists()

    /** Creates a session in the requested mode; a failing accelerator falls back to plain CPU with a warn log. */
    fun open(
        env: OrtEnvironment,
        file: File,
        mode: Mode,
        threads: Int = defaultThreads(),
        cacheDir: File? = null
    ): Opened {
        val name = file.name
        if (mode == Mode.QNN && cacheDir != null) {
            try {
                return openQnn(env, file, threads, cacheDir)
            } catch (t: Throwable) {
                warn("ep-fallback", t, mapOf("model" to name, "wanted" to "qnn", "using" to "cpu"))
            }
        } else if (mode == Mode.XNNPACK) {
            try {
                val o = base(1).apply { addXnnpack(mapOf("intra_op_num_threads" to threads.toString())) }
                return Opened(env.createSession(file.absolutePath, o), "xnnpack")
            } catch (t: Throwable) {
                warn("ep-fallback", t, mapOf("model" to name, "wanted" to "xnnpack", "using" to "cpu"))
            }
        }
        return Opened(env.createSession(file.absolutePath, base(threads)), "cpu")
    }

    private fun qnnOptions(threads: Int): OrtSession.SessionOptions = base(threads).apply {
        addQnn(
            mapOf(
                "backend_path" to "libQnnHtp.so",
                "htp_performance_mode" to "burst",
                "enable_htp_fp16_precision" to "1",
                "htp_graph_finalization_optimization_mode" to "3"
            )
        )
    }

    /**
     * Strict QNN open (throws on failure). Reuses the compiled context when present; a context that no longer loads is
     * deleted and the model recompiled. A model whose compile fails is marked so later starts do not retry it.
     */
    fun openQnn(env: OrtEnvironment, file: File, threads: Int, cacheDir: File): Opened {
        cacheDir.mkdirs()
        val ctx = ctxFile(file, cacheDir)
        val mark = failedMark(file, cacheDir)
        if (mark.exists()) error("qnn compile failed on an earlier start (${mark.name})")
        if (ctx.isFile && ctx.length() > 0) {
            try {
                return Opened(env.createSession(ctx.absolutePath, qnnOptions(threads)), "qnn-htp", true)
            } catch (t: Throwable) {
                warn("qnn-ctx-invalid", t, mapOf("model" to file.name))
                ctx.delete()
            }
        }
        val prefix = file.name.removeSuffix(".onnx") + "_"
        cacheDir.listFiles()
            ?.filter { it.name.startsWith(prefix) && it.name.endsWith("_ctx.onnx") && it != ctx }
            ?.forEach { it.delete() } // stale contexts of older model files / versions
        val opts = qnnOptions(threads)
        opts.addConfigEntry("ep.context_enable", "1")
        opts.addConfigEntry("ep.context_embed_mode", "1")
        opts.addConfigEntry("ep.context_file_path", ctx.absolutePath)
        try {
            return Opened(env.createSession(file.absolutePath, opts), "qnn-htp", false)
        } catch (t: Throwable) {
            runCatching { mark.writeText(t.toString().take(300)) }
            throw t
        }
    }
}
