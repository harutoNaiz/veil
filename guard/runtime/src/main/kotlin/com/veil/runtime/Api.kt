package com.veil.runtime

sealed interface Tensor {
    val shape: LongArray
}

class FloatTensor(override val shape: LongArray, val data: FloatArray) : Tensor

class LongTensor(override val shape: LongArray, val data: LongArray) : Tensor

data class IoSpec(val name: String, val shape: LongArray, val dtype: String)

data class ModelSpec(val id: String, val path: String, val inputs: List<IoSpec>, val outputs: List<IoSpec>)

enum class Backend { NPU, CPU }

class LoadedModel(
    val spec: ModelSpec,
    val backend: Backend,
    val loadMs: Double,
    val fromCache: Boolean,
    val handle: Any
)

class RuntimeFailure(message: String, cause: Throwable? = null) : RuntimeException(message, cause)

interface ModelRuntime : AutoCloseable {
    val name: String

    fun load(spec: ModelSpec, config: RuntimeConfig = RuntimeConfig()): LoadedModel

    fun run(model: LoadedModel, inputs: Map<String, Tensor>): Map<String, Tensor>

    fun release(model: LoadedModel)
}
