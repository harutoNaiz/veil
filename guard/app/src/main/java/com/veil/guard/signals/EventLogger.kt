package com.veil.guard.signals

import android.os.SystemClock
import android.util.Log
import java.io.File
import java.io.FileWriter
import java.util.concurrent.Executors
import java.util.concurrent.ScheduledFuture
import java.util.concurrent.TimeUnit

/** JSONL logging mode: filesDir/signals/<name>.events.jsonl plus <name>.clock.json. Driven by LogControlReceiver. */
class EventLogger(private val dir: File) {
    private var writer: FileWriter? = null
    private var flusher: ScheduledFuture<*>? = null
    private var pumped: BoundedSnapshotter? = null
    private val exec = Executors.newSingleThreadScheduledExecutor()

    @Volatile var active = false
        private set

    @Synchronized
    fun start(name: String, snapshotter: BoundedSnapshotter?) {
        if (active) stop()
        val safe = name.replace(Regex("[^A-Za-z0-9_.-]"), "_").ifEmpty { "log" }
        dir.mkdirs()
        File(dir, "$safe.clock.json").writeText(
            "{\"uptimeMs\":${SystemClock.uptimeMillis()},\"elapsedRealtimeMs\":${SystemClock.elapsedRealtime()}}"
        )
        writer = FileWriter(File(dir, "$safe.events.jsonl"), false)
        flusher = exec.scheduleWithFixedDelay({ flush() }, 500, 500, TimeUnit.MILLISECONDS)
        active = true
        pumped = snapshotter
        snapshotter?.startPump(::write)
        Log.i(TAG, "VEIL_LOG start $safe")
    }

    @Synchronized
    fun stop() {
        if (!active) return
        pumped?.stopPump()
        pumped = null
        active = false
        flusher?.cancel(false)
        writer?.flush()
        writer?.close()
        writer = null
        Log.i(TAG, "VEIL_LOG stop")
    }

    @Synchronized
    fun write(event: UiEvent) {
        val w = writer ?: return
        w.write(UiEventJson.toJson(event))
        w.write("\n")
    }

    @Synchronized
    private fun flush() {
        writer?.flush()
    }

    companion object {
        private const val TAG = "VeilSignals"

        @Volatile var instance: EventLogger? = null
    }
}
