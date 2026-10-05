package com.veil.smoketest

import android.app.Activity
import android.os.Bundle
import android.util.Log
import android.widget.TextView
import com.veil.runtime.FloatTensor
import com.veil.runtime.LongTensor
import com.veil.runtime.ModelSpec
import com.veil.runtime.ResidentModels
import com.veil.runtime.RuntimeConfig
import com.veil.runtime.Tensor
import com.veil.runtime.latencyOf
import com.veil.runtime.ort.OrtQnnRuntime
import java.io.File

class MainActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val tv = TextView(this)
        setContentView(tv)
        val mode = intent.getStringExtra("mode") ?: "ready"
        Thread {
            val text = try {
                runMode(mode)
            } catch (e: Throwable) {
                Log.e("VEIL", "failed", e)
                "FAILED: ${e.message}"
            }
            runOnUiThread { tv.text = text }
        }.start()
    }

    private fun dummy(spec: ModelSpec): Map<String, Tensor> = spec.inputs.associate {
        val n = it.shape.fold(1L) { a, b -> a * b }.toInt()
        it.name to
            (
                if (it.dtype ==
                    "int64"
                ) {
                    LongTensor(it.shape, LongArray(n) { 1L })
                } else {
                    FloatTensor(it.shape, FloatArray(n))
                }
                )
    }

    private fun runMode(mode: String): String {
        val dir = externalMediaDirs[0]
        val specs = Manifests.loadAll(dir)
        val cache = File(dir, "cache").also { it.mkdirs() }
        val cfg = RuntimeConfig(cacheDir = cache.path, profileDir = File(dir, "out").also { it.mkdirs() }.path)
        OrtQnnRuntime(this).use { rt ->
            ResidentModels(rt, specs, cfg, 2, ::dummy).use { rm ->
                val ready = rm.start()
                Log.i("VEIL", "VEIL_READY ms=$ready cache=${cache.list()?.isNotEmpty() == true}")
                if (mode != "pt") return "ready in $ready ms"
                val ms = DoubleArray(50) {
                    val t0 = System.nanoTime()
                    specs.forEach { s -> rm.run(s.id, dummy(s)) }
                    (System.nanoTime() - t0) / 1e6
                }
                val l = latencyOf(ms)
                File(dir, "out/pt.txt").writeText("p50=${l.p50} p95=${l.p95}\n")
                return "ready $ready ms; look p50=${l.p50} p95=${l.p95}"
            }
        }
    }
}
