package com.veil.guard.wire.ml

import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import android.content.Context
import com.veil.guard.wire.WireHub
import java.io.File

/** ONNX sessions from <externalMedia>/models, cached by file name. CPU EP, 4 intra-op threads. */
class ModelStore(private val ctx: Context) {
    val env: OrtEnvironment = OrtEnvironment.getEnvironment()

    val dir: File get() = File(ctx.externalMediaDirs.first(), "models")

    fun session(name: String): OrtSession? = open(env, dir, name)

    fun has(name: String): Boolean = File(dir, name).isFile

    private companion object {
        val cache = HashMap<String, Pair<Long, OrtSession>>()

        @Synchronized
        fun open(env: OrtEnvironment, dir: File, name: String): OrtSession? {
            val f = File(dir, name)
            if (!f.isFile) {
                WireHub.log?.write(mapOf("kind" to "warn", "what" to "model-missing", "file" to name))
                return null
            }
            val stamp = f.lastModified() xor f.length()
            cache[name]?.let { (st, s) ->
                if (st == stamp) return s
                runCatching { s.close() }
            }
            val opts = OrtSession.SessionOptions().apply { setIntraOpNumThreads(4) }
            return env.createSession(f.absolutePath, opts).also { cache[name] = stamp to it }
        }
    }
}
