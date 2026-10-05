package com.veil.smoketest

import android.os.Debug
import androidx.test.platform.app.InstrumentationRegistry
import com.veil.runtime.ResidentModels
import com.veil.runtime.RuntimeConfig
import com.veil.runtime.latencyOf
import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

class ResidentTest {
    @Test
    fun resident() {
        val args = InstrumentationRegistry.getArguments()
        val n = (args.getString("n") ?: "1000").toInt()
        val dir = mediaDir()
        val specs = Manifests.loadAll(dir)
        val cfg = RuntimeConfig(cacheDir = File(dir, "cache").also { it.mkdirs() }.path)
        val csv = StringBuilder("runtime,model,phase,i,ms\n")
        val rtName = args.getString("runtime") ?: "ort-qnn"
        runtimeFor(rtName).use { rt ->
            ResidentModels(rt, specs, cfg, 2, ::dummyInputs).use { rm ->
                rm.start()
                for (s in specs) {
                    val inp = dummyInputs(s)
                    val ms = DoubleArray(n) {
                        val t0 = System.nanoTime()
                        rm.run(s.id, inp)
                        (System.nanoTime() - t0) / 1e6
                    }
                    ms.forEachIndexed { i, v -> csv.append("$rtName,${s.id},warm,$i,$v\n") }
                    assertTrue(latencyOf(ms).p95 > 0)
                }
                Thread.sleep(30_000)
                val s0 = specs.first()
                val t0 = System.nanoTime()
                rm.run(s0.id, dummyInputs(s0))
                csv.append("$rtName,${s0.id},idle-first,0,${(System.nanoTime() - t0) / 1e6}\n")
                val pss = Debug.getPss()
                assertTrue("PSS ${pss}kB over 3 GB", pss <= 3L * 1024 * 1024)
            }
        }
        File(dir, "out").also { it.mkdirs() }.let { File(it, "timing.csv").writeText(csv.toString()) }
    }
}
