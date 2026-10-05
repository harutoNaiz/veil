package com.veil.guard.overlay.self

import android.accessibilityservice.AccessibilityService
import com.veil.guard.overlay.OverlayCommands
import com.veil.guard.overlay.OverlayHub
import java.io.File

/** Wires own-cover reporting and the peek probe to the debug commands. Host calls [install] on connect. */
object SelfCapture {
    private var registry: OwnOverlayRegistry? = null

    val current: OwnOverlayRegistry? get() = registry

    fun install(service: AccessibilityService) {
        val dir = File(service.filesDir, "overlay").apply { mkdirs() }
        OverlayCommands.handlers["selfcap"] = { v ->
            val on = v != "off"
            registry?.let { OverlayHub.drawnListeners.remove(it) }
            registry = null
            if (on) {
                val r = OwnOverlayRegistry(logFile = File(dir, "own.jsonl"))
                registry = r
                OverlayHub.drawnListeners.add(r)
            }
        }
        OverlayCommands.handlers["peekprobe"] = { PeekProbe.run(service, File(dir, "peek.jsonl"), dir) }
    }

    fun uninstall() {
        registry?.let { OverlayHub.drawnListeners.remove(it) }
        registry = null
        OverlayCommands.handlers.remove("selfcap")
        OverlayCommands.handlers.remove("peekprobe")
    }
}
