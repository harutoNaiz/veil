package com.veil.console

import android.os.Handler
import android.os.Looper
import com.veil.console.bridge.GuardBackend
import com.veil.console.bridge.GuardHostApi
import com.veil.console.bridge.GuardHostImpl
import com.veil.console.bridge.PigeonEventSink
import com.veil.console.bridge.RemoteGuardBackend
import com.veil.console.bridge.StateMsg
import com.veil.console.bridge.StatsMsg
import com.veil.console.bridge.StreamStateStreamHandler
import com.veil.console.bridge.StreamStatsStreamHandler
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine

class MainActivity : FlutterActivity() {
    private val main = Handler(Looper.getMainLooper())

    private fun every(ms: Long, work: () -> Unit): Runnable {
        val r = object : Runnable {
            override fun run() {
                work()
                main.postDelayed(this, ms)
            }
        }
        main.postDelayed(r, ms)
        return r
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        val backend: GuardBackend = RemoteGuardBackend(this)
        val m = flutterEngine.dartExecutor.binaryMessenger
        GuardHostApi.setUp(m, GuardHostImpl(backend))
        StreamStateStreamHandler.register(m, object : StreamStateStreamHandler() {
            private var poll: Runnable? = null

            override fun onListen(p0: Any?, sink: PigeonEventSink<StateMsg>) {
                poll = every(2000) {
                    Thread {
                        runCatching { backend.getState() }.getOrNull()?.let { s -> main.post { sink.success(s) } }
                    }.start()
                }
            }

            override fun onCancel(p0: Any?) {
                poll?.let { main.removeCallbacks(it) }
            }
        })
        StreamStatsStreamHandler.register(m, object : StreamStatsStreamHandler() {
            private var poll: Runnable? = null

            override fun onListen(p0: Any?, sink: PigeonEventSink<StatsMsg>) {
                poll = every(1000) { sink.success(StatsMsg(System.currentTimeMillis(), 0.0, 0.0, 0.0, 0L)) }
            }

            override fun onCancel(p0: Any?) {
                poll?.let { main.removeCallbacks(it) }
            }
        })
    }
}
