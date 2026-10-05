package com.veil.guard.wire.ml

import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import android.content.Context
import com.veil.guard.wire.WireHub
import java.io.File

/** ONNX sessions from <externalMedia>/models, cached by file name. CPU EP, 4 intra-op threads. */
class ModelStore(private val ctx: Context) {
    val env: OrtEnvironment = OrtEnvironment.getEnvironment()
    private val cache = HashMap<String, OrtSession>()

    val dir: File get() = File(ctx.externalMediaDirs.first(), "models")

    @Synchronized
    fun session(name: String): OrtSession? {
        cache[name]?.let { return it }
        val f = File(dir, name)
        if (!f.isFile) {
            WireHub.log?.write(mapOf("kind" to "warn", "what" to "model-missing", "file" to name))
            return null
        }
        val opts = OrtSession.SessionOptions().apply { setIntraOpNumThreads(4) }
        return env.createSession(f.absolutePath, opts).also { cache[name] = it }
    }

    fun has(name: String): Boolean = File(dir, name).isFile
}
