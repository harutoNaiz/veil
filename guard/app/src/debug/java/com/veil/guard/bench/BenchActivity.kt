package com.veil.guard.bench

import android.app.Activity
import android.os.Bundle
import com.veil.guard.wire.ml.accel.MlBench

/** Debug-only: `adb shell am start -n com.veil.guard/.bench.BenchActivity` runs MlBench; results in files/bench.json and media/bench.json. */
class BenchActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        Thread {
            runCatching { MlBench.run(applicationContext, intent.getIntExtra("iters", 5)) }
                .onFailure { android.util.Log.e("VEIL_BENCH", "bench failed", it) }
            finish()
        }.start()
    }
}
