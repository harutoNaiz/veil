package com.veil.testfeed

import java.io.BufferedWriter
import java.io.File

/** Writes one line per call to [file]. The file is truncated when the logger is created. */
class FeedLogger(file: File) {
    private val writer: BufferedWriter = file.bufferedWriter(Charsets.UTF_8)
    private var closed = false

    @Synchronized
    fun log(line: String) {
        if (closed) return
        writer.write(line)
        writer.write("\n")
    }

    @Synchronized
    fun flush() {
        if (!closed) writer.flush()
    }

    @Synchronized
    fun close() {
        if (closed) return
        closed = true
        writer.close()
    }
}
