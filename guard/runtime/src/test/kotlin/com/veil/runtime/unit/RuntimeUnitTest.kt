package com.veil.runtime.unit

import com.veil.runtime.Backend
import com.veil.runtime.ImagePrep
import com.veil.runtime.LoadedModel
import com.veil.runtime.ModelRuntime
import com.veil.runtime.ModelSpec
import com.veil.runtime.PerfMode
import com.veil.runtime.ProfileCheck
import com.veil.runtime.ResidentModels
import com.veil.runtime.RuntimeConfig
import com.veil.runtime.RuntimeFailure
import com.veil.runtime.Tensor
import com.veil.runtime.latencyOf
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test

class FakeRuntime(private val failOn: String? = null) : ModelRuntime {
    override val name = "fake"
    val threads = mutableSetOf<String>()
    val released = mutableListOf<String>()
    var runs = 0

    override fun load(spec: ModelSpec, config: RuntimeConfig): LoadedModel {
        threads += Thread.currentThread().name
        if (spec.id == failOn) throw RuntimeFailure("boom")
        return LoadedModel(spec, Backend.NPU, 1.0, false, Any())
    }

    override fun run(model: LoadedModel, inputs: Map<String, Tensor>): Map<String, Tensor> {
        threads += Thread.currentThread().name
        runs++
        return inputs
    }

    override fun release(model: LoadedModel) {
        released += model.spec.id
    }

    override fun close() {}
}

class RuntimeUnitTest {
    private fun spec(id: String) = ModelSpec(id, "$id.onnx", emptyList(), emptyList())

    @Test fun defaultConfigDisablesFallback() {
        val e = RuntimeConfig().ortSessionEntries("m", false)
        assertEquals("1", e["session.disable_cpu_ep_fallback"])
        assertEquals(1, e.size)
        val allowed = RuntimeConfig(allowCpuFallback = true).ortSessionEntries("m", false)
        assertFalse(allowed.containsKey("session.disable_cpu_ep_fallback"))
    }

    @Test fun cacheEntries() {
        val c = RuntimeConfig(cacheDir = "/c")
        assertEquals("/c/m_ctx.onnx", c.cachePath("m"))
        assertEquals("1", c.ortSessionEntries("m", false)["ep.context_enable"])
        assertFalse(c.ortSessionEntries("m", true).containsKey("ep.context_enable"))
        assertNull(RuntimeConfig().cachePath("m"))
    }

    @Test fun runEntries() {
        assertEquals("burst", RuntimeConfig().ortRunEntries()["qnn.htp_perf_mode"])
        assertEquals("low_power_saver", RuntimeConfig().ortRunEntries()["qnn.htp_perf_mode_post_run"])
        val d = RuntimeConfig(runPerfMode = PerfMode.DEFAULT).qnnProviderOptions("/d")
        assertEquals("default", d["htp_performance_mode"])
    }

    @Test fun latency() {
        val l = latencyOf(DoubleArray(100) { it + 1.0 })
        assertEquals(50.0, l.p50, 0.0)
        assertEquals(95.0, l.p95, 0.0)
        assertEquals(100.0, l.max, 0.0)
    }

    @Test fun profileCheck() {
        val npu = """[{"cat":"Node","args":{"provider":"QNNExecutionProvider"}},{"cat":"Session","name":"s"}]"""
        val mixed = """[{"cat":"Node","args":{"provider":"QNNExecutionProvider"}},""" +
            """{"cat":"Node","args":{"provider":"CPUExecutionProvider"}}]"""
        assertTrue(ProfileCheck.allOnNpu(npu))
        assertFalse(ProfileCheck.allOnNpu(mixed))
        assertEquals(1, ProfileCheck.providerCounts(mixed)["CPUExecutionProvider"])
    }

    @Test fun residentModels() {
        val rt = FakeRuntime()
        val r = ResidentModels(rt, listOf(spec("a"), spec("b")), RuntimeConfig()) { emptyMap() }
        r.start()
        assertEquals(4, rt.runs)
        r.run("a", emptyMap())
        assertEquals(setOf("veil-ai"), rt.threads)
        r.close()
        assertEquals(listOf("a", "b"), rt.released)
    }

    @Test fun loadFailurePropagates() {
        val r = ResidentModels(FakeRuntime("b"), listOf(spec("a"), spec("b")), RuntimeConfig()) { emptyMap() }
        try {
            r.start()
            fail()
        } catch (e: RuntimeFailure) {
            assertEquals("boom", e.message)
        } finally {
            r.close()
        }
    }

    @Test fun imagePrep() {
        val px = intArrayOf(0xFF0A141E.toInt(), 0xFF28323C.toInt())
        val o = ImagePrep.nchw(px, 2, 1, 1f, floatArrayOf(0f, 0f, 0f), floatArrayOf(10f, 10f, 10f))
        assertEquals(listOf(1f, 4f, 2f, 5f, 3f, 6f), o.toList())
    }
}
