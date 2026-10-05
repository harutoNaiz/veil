package com.veil.runtime

import java.util.concurrent.Callable
import java.util.concurrent.ExecutionException
import java.util.concurrent.Executors

class SerialWorker : AutoCloseable {
    private val ex = Executors.newSingleThreadExecutor { r -> Thread(r, "veil-ai") }

    fun <T> call(block: () -> T): T = try {
        ex.submit(Callable { block() }).get()
    } catch (e: ExecutionException) {
        throw e.cause ?: e
    }

    override fun close() {
        ex.shutdown()
    }
}

class ResidentModels(
    private val rt: ModelRuntime,
    private val specs: List<ModelSpec>,
    private val cfg: RuntimeConfig,
    private val warmups: Int = 2,
    private val inputs: (ModelSpec) -> Map<String, Tensor>
) : AutoCloseable {
    private val worker = SerialWorker()
    private val loaded = LinkedHashMap<String, LoadedModel>()

    fun start(): Long {
        val t0 = System.nanoTime()
        worker.call {
            for (s in specs) {
                val m = rt.load(s, cfg)
                loaded[s.id] = m
                val inp = inputs(s)
                repeat(warmups) { rt.run(m, inp) }
            }
        }
        return (System.nanoTime() - t0) / 1_000_000
    }

    fun run(id: String, inputs: Map<String, Tensor>): Map<String, Tensor> = worker.call {
        val m = loaded[id] ?: throw RuntimeFailure("model not loaded: $id")
        rt.run(m, inputs)
    }

    override fun close() {
        try {
            worker.call {
                loaded.values.forEach { rt.release(it) }
                loaded.clear()
            }
        } finally {
            worker.close()
        }
    }
}
