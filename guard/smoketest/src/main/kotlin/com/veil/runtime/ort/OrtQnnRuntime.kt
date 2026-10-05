package com.veil.runtime.ort

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import android.content.Context
import android.system.Os
import com.veil.runtime.Backend
import com.veil.runtime.FloatTensor
import com.veil.runtime.LoadedModel
import com.veil.runtime.LongTensor
import com.veil.runtime.ModelRuntime
import com.veil.runtime.ModelSpec
import com.veil.runtime.RuntimeConfig
import com.veil.runtime.RuntimeFailure
import com.veil.runtime.Tensor
import java.io.File
import java.nio.FloatBuffer
import java.nio.LongBuffer

/** ONNX Runtime + QNN HTP wrapper. CPU fallback is off unless the config allows it. */
class OrtQnnRuntime(context: Context) : ModelRuntime {
    override val name = "ort-qnn"
    private val libDir = context.applicationInfo.nativeLibraryDir
    private val env: OrtEnvironment by lazy {
        Os.setenv("ADSP_LIBRARY_PATH", libDir, true)
        OrtEnvironment.getEnvironment()
    }

    private class Handle(val session: OrtSession, val config: RuntimeConfig)

    override fun load(spec: ModelSpec, config: RuntimeConfig): LoadedModel {
        try {
            val t0 = System.nanoTime()
            val cache = config.cachePath(spec.id)
            val cacheExists = cache != null && File(cache).exists()
            val opts = OrtSession.SessionOptions()
            config.ortSessionEntries(spec.id, cacheExists).forEach { (k, v) -> opts.addConfigEntry(k, v) }
            opts.addQnn(config.qnnProviderOptions(libDir))
            config.profileDir?.let { opts.enableProfiling("$it/${spec.id}") }
            val path = if (cacheExists) cache!! else spec.path
            val session = env.createSession(path, opts)
            val ms = (System.nanoTime() - t0) / 1e6
            return LoadedModel(spec, Backend.NPU, ms, cacheExists, Handle(session, config))
        } catch (e: Throwable) {
            throw RuntimeFailure("ort-qnn load failed for ${spec.id}: ${e.message}", e)
        }
    }

    override fun run(model: LoadedModel, inputs: Map<String, Tensor>): Map<String, Tensor> {
        val h = model.handle as Handle
        val created = mutableListOf<OnnxTensor>()
        try {
            val feed = HashMap<String, OnnxTensor>()
            for ((n, t) in inputs) {
                val ot = when (t) {
                    is FloatTensor -> OnnxTensor.createTensor(env, FloatBuffer.wrap(t.data), t.shape)
                    is LongTensor -> OnnxTensor.createTensor(env, LongBuffer.wrap(t.data), t.shape)
                }
                created += ot
                feed[n] = ot
            }
            OrtSession.RunOptions().use { ro ->
                h.config.ortRunEntries().forEach { (k, v) -> ro.addRunConfigEntry(k, v) }
                h.session.run(feed, ro).use { res ->
                    val out = LinkedHashMap<String, Tensor>()
                    for (o in model.spec.outputs) {
                        val v = res.get(o.name).get() as OnnxTensor
                        val shape = v.info.shape
                        out[o.name] = when (o.dtype) {
                            "int64" -> LongTensor(
                                shape,
                                LongArray(v.longBuffer.remaining()).also {
                                    v.longBuffer.get(it)
                                }
                            )

                            else -> FloatTensor(
                                shape,
                                FloatArray(v.floatBuffer.remaining()).also {
                                    v.floatBuffer.get(it)
                                }
                            )
                        }
                    }
                    return out
                }
            }
        } catch (e: Throwable) {
            throw RuntimeFailure("ort-qnn run failed for ${model.spec.id}: ${e.message}", e)
        } finally {
            created.forEach { it.close() }
        }
    }

    override fun release(model: LoadedModel) {
        try {
            (model.handle as Handle).session.close()
        } catch (e: Throwable) {
            throw RuntimeFailure("ort-qnn release failed: ${e.message}", e)
        }
    }

    override fun close() = Unit
}
