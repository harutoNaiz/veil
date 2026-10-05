package com.veil.guard.capture

import android.content.Context
import java.io.File
import java.util.concurrent.locks.ReentrantLock

/**
 * Appends one JSON object per line to files/capture/frames.jsonl and files/capture/state.jsonl.
 * Callers build the JSON (contractVersion "1.0" for frames); this class only owns the file I/O.
 */
class CaptureLog(context: Context) {
    private val dir = File(context.filesDir, "capture").apply { mkdirs() }
    private val framesFile = File(dir, "frames.jsonl")
    private val stateFile = File(dir, "state.jsonl")
    private val lock = ReentrantLock()

    fun appendFrame(json: String) = append(framesFile, json)

    fun appendState(json: String) = append(stateFile, json)

    private fun append(file: File, json: String) {
        lock.lock()
        try {
            file.appendText(json + "\n")
        } finally {
            lock.unlock()
        }
    }
}
