package com.veil.runtime.litert

import com.google.ai.edge.litert.Accelerator
import com.google.ai.edge.litert.CompiledModel
import com.veil.runtime.Backend
import com.veil.runtime.FloatTensor
import com.veil.runtime.LoadedModel
import com.veil.runtime.ModelRuntime
import com.veil.runtime.ModelSpec
import com.veil.runtime.RuntimeConfig
import com.veil.runtime.RuntimeFailure
import com.veil.runtime.Tensor
import java.io.File

/** LiteRT CompiledModel wrapper, NPU accelerator only (no CPU/GPU fallback). Float tensors only. */
class LiteRtRuntime : ModelRuntime {
    override val name = "litert-npu"

    private class Handle(val model: CompiledModel)

    override fun load(spec: ModelSpec, config: RuntimeConfig): LoadedModel {
        try {
            if (!File(spec.path).exists()) throw IllegalStateException("missing .tflite: ${spec.path}")
            val t0 = System.nanoTime()
            val m = CompiledModel.create(spec.path, CompiledModel.Options(Accelerator.NPU))
            return LoadedModel(spec, Backend.NPU, (System.nanoTime() - t0) / 1e6, false, Handle(m))
        } catch (e: Throwable) {
            throw RuntimeFailure("litert-npu load failed for ${spec.id}: ${e.message}", e)
        }
    }

    override fun run(model: LoadedModel, inputs: Map<String, Tensor>): Map<String, Tensor> {
        val m = (model.handle as Handle).model
        try {
            val inBufs = m.createInputBuffers()
            val outBufs = m.createOutputBuffers()
            try {
                model.spec.inputs.forEachIndexed { i, io ->
                    val t =
                        inputs[io.name] as? FloatTensor
                            ?: throw IllegalArgumentException("float input ${io.name} missing")
                    inBufs[i].writeFloat(t.data)
                }
                m.run(inBufs, outBufs)
                val out = LinkedHashMap<String, Tensor>()
                model.spec.outputs.forEachIndexed { i, io ->
                    out[io.name] =
                        FloatTensor(io.shape, outBufs[i].readFloat())
                }
                return out
            } finally {
                inBufs.forEach { it.close() }
                outBufs.forEach { it.close() }
            }
        } catch (e: Throwable) {
            throw RuntimeFailure("litert-npu run failed for ${model.spec.id}: ${e.message}", e)
        }
    }

    override fun release(model: LoadedModel) {
        (model.handle as Handle).model.close()
    }

    override fun close() = Unit
}
