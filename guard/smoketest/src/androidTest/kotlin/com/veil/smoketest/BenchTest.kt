package com.veil.smoketest

import androidx.test.platform.app.InstrumentationRegistry
import com.veil.runtime.FloatTensor
import com.veil.runtime.LongTensor
import com.veil.runtime.ModelRuntime
import com.veil.runtime.ModelSpec
import com.veil.runtime.ProfileCheck
import com.veil.runtime.RuntimeConfig
import com.veil.runtime.Tensor
import com.veil.runtime.litert.LiteRtRuntime
import com.veil.runtime.ort.OrtQnnRuntime
import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

internal fun dummyInputs(spec: ModelSpec): Map<String, Tensor> = spec.inputs.associate {
    val n = it.shape.fold(1L) { a, b -> a * b }.toInt()
    it.name to
        (if (it.dtype == "int64") LongTensor(it.shape, LongArray(n) { 1L }) else FloatTensor(it.shape, FloatArray(n)))
}

internal fun runtimeFor(name: String): ModelRuntime {
    val ctx = InstrumentationRegistry.getInstrumentation().targetContext
    return if (name == "litert-npu") LiteRtRuntime() else OrtQnnRuntime(ctx)
}

internal fun mediaDir(): File = InstrumentationRegistry.getInstrumentation().targetContext.externalMediaDirs[0]

class BenchTest {
    @Test
    fun bench() {
        val args = InstrumentationRegistry.getArguments()
        val model = args.getString("model") ?: "siglip2-image-b1"
        val n = (args.getString("n") ?: "100").toInt()
        val dir = mediaDir()
        val out = File(dir, "out").also { it.mkdirs() }
        val spec = Manifests.loadAll(dir).first { it.id == model }
        val rtName = args.getString("runtime") ?: "ort-qnn"
        runtimeFor(rtName).use { rt ->
            val cfg = RuntimeConfig(cacheDir = File(dir, "cache").also { it.mkdirs() }.path, profileDir = out.path)
            val m = rt.load(spec, cfg)
            val inp = dummyInputs(spec)
            val csv = StringBuilder("runtime,model,phase,i,ms\n")
            for (i in 0 until n) {
                val t0 = System.nanoTime()
                rt.run(m, inp)
                csv.append("$rtName,$model,${if (i == 0) "cold" else "warm"},$i,${(System.nanoTime() - t0) / 1e6}\n")
            }
            rt.release(m)
            File(out, "timing.csv").writeText(csv.toString())
        }
        if (rtName == "ort-qnn") {
            val prof = out.listFiles { f ->
                f.name.startsWith(model) && f.name.endsWith(".json")
            }?.maxByOrNull { it.lastModified() }
            assertTrue("no ORT profile written", prof != null)
            assertTrue("nodes ran off the NPU", ProfileCheck.allOnNpu(prof!!.readText()))
        }
    }
}
