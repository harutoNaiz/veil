package com.veil.guard.wire.ml

import android.os.FileObserver
import java.io.File

/** Calls [onChange] when a *.json file in [dir] is written, moved in or removed. */
class ConceptWatcher(private val dir: File, private val onChange: () -> Unit) {
    private var obs: FileObserver? = null

    fun start() {
        if (obs != null) return
        val mask = FileObserver.CLOSE_WRITE or FileObserver.MOVED_TO or FileObserver.DELETE or FileObserver.MOVED_FROM
        obs =
            object : FileObserver(dir, mask) {
                override fun onEvent(event: Int, path: String?) {
                    if (path != null && path.endsWith(".json")) onChange()
                }
            }.also { it.startWatching() }
    }

    fun stop() {
        obs?.stopWatching()
        obs = null
    }
}
