package com.veil.guard.wire

import android.os.Trace
import com.veil.brain.contract.Finding
import com.veil.conductor.AiWorker
import java.util.concurrent.Executors

/** Runs jobs on one `veil-ai` thread; `done` is posted back via [post] (the conductor thread). */
class ThreadWorker(private val post: (Runnable) -> Unit, private val onDone: () -> Unit) : AiWorker {
    private val exec = Executors.newSingleThreadExecutor { r -> Thread(r, "veil-ai") }

    @Volatile private var inFlight = false

    override val busy: Boolean get() = inFlight

    override fun submit(job: () -> List<Finding>, done: (List<Finding>, Long) -> Unit) {
        inFlight = true
        // A look scheduled just as protection stops reaches a shut-down executor: drop it, do not crash.
        try {
            run(job, done)
        } catch (e: java.util.concurrent.RejectedExecutionException) {
            inFlight = false
        }
    }

    private fun run(job: () -> List<Finding>, done: (List<Finding>, Long) -> Unit) {
        exec.execute {
            val t0 = System.nanoTime()
            val found =
                runCatching {
                    Trace.beginSection("veil.lanes")
                    try {
                        job()
                    } finally {
                        Trace.endSection()
                    }
                }.getOrElse {
                    WireHub.log?.write(linkedMapOf("kind" to "warn", "what" to "lanes-failed", "why" to it.toString()))
                    emptyList()
                }
            val ms = (System.nanoTime() - t0) / 1_000_000
            post(
                Runnable {
                    // Free before done(): the conductor may start a confirm look from inside it.
                    inFlight = false
                    try {
                        done(found, ms)
                    } finally {
                        onDone()
                    }
                }
            )
        }
    }

    fun shutdown() {
        exec.shutdownNow()
    }
}
