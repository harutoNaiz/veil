package com.veil.runtime

enum class PerfMode(val qnn: String) {
    BURST("burst"),
    LOW_POWER("low_power_saver"),
    DEFAULT("default")
}

data class RuntimeConfig(
    val allowCpuFallback: Boolean = false,
    val runPerfMode: PerfMode = PerfMode.BURST,
    val idlePerfMode: PerfMode = PerfMode.LOW_POWER,
    val fp16: Boolean = true,
    val cacheDir: String? = null,
    val profileDir: String? = null
) {
    fun cachePath(id: String): String? = cacheDir?.let { "$it/${id}_ctx.onnx" }

    fun ortSessionEntries(id: String, cacheExists: Boolean): Map<String, String> {
        val m = LinkedHashMap<String, String>()
        if (!allowCpuFallback) m["session.disable_cpu_ep_fallback"] = "1"
        val path = cachePath(id)
        if (path != null && !cacheExists) {
            m["ep.context_enable"] = "1"
            m["ep.context_embed_mode"] = "1"
            m["ep.context_file_path"] = path
        }
        return m
    }

    fun qnnProviderOptions(nativeLibDir: String): Map<String, String> = linkedMapOf(
        "backend_path" to "$nativeLibDir/libQnnHtp.so",
        "htp_performance_mode" to runPerfMode.qnn,
        "enable_htp_fp16_precision" to if (fp16) "1" else "0",
        "htp_graph_finalization_optimization_mode" to "3"
    )

    fun ortRunEntries(): Map<String, String> = linkedMapOf(
        "qnn.htp_perf_mode" to runPerfMode.qnn,
        "qnn.htp_perf_mode_post_run" to idlePerfMode.qnn
    )
}
