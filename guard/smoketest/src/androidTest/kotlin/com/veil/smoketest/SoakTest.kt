package com.veil.smoketest

import android.content.Context
import android.os.Debug
import android.os.PowerManager
import androidx.test.platform.app.InstrumentationRegistry
import com.veil.runtime.ResidentModels
import com.veil.runtime.RuntimeConfig
import com.veil.runtime.RuntimeFailure
import java.io.File
import org.junit.Test

class SoakTest {
    @Test
    fun soak() {
        val args = InstrumentationRegistry.getArguments()
        val minutes = (args.getString("minutes") ?: "10").toInt()
        val rate = (args.getString("rate") ?: "3").toInt()
        val ctx = InstrumentationRegistry.getInstrumentation().targetContext
        val pm = ctx.getSystemService(Context.POWER_SERVICE) as PowerManager
        val dir = mediaDir()
        val specs = Manifests.loadAll(dir)
        val cfg = RuntimeConfig(cacheDir = File(dir, "cache").also { it.mkdirs() }.path)
        val csv = StringBuilder("tMs,lookMs,ok,pssKb,thermal,headroom\n")
        runtimeFor(args.getString("runtime") ?: "ort-qnn").use { rt ->
            ResidentModels(rt, specs, cfg, 2, ::dummyInputs).use { rm ->
                rm.start()
                val start = System.nanoTime()
                val end = start + minutes * 60_000_000_000L
                var next = start
                while (System.nanoTime() < end) {
                    val t0 = System.nanoTime()
                    val ok = try {
                        specs.forEach { rm.run(it.id, dummyInputs(it)) }
                        1
                    } catch (e: RuntimeFailure) {
                        0
                    }
                    val now = System.nanoTime()
                    csv.append("${(t0 - start) / 1_000_000},${(now - t0) / 1e6},$ok,${Debug.getPss()},")
                    csv.append("${pm.currentThermalStatus},${pm.getThermalHeadroom(10)}\n")
                    next += 1_000_000_000L / rate
                    val wait = (next - System.nanoTime()) / 1_000_000
                    if (wait > 0) Thread.sleep(wait)
                }
            }
        }
        File(dir, "out").also { it.mkdirs() }.let { File(it, "soak.csv").writeText(csv.toString()) }
    }
}
