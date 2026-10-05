package com.veil.guard.overlay.self

import android.accessibilityservice.AccessibilityService
import android.graphics.Bitmap
import android.os.Build
import android.os.SystemClock
import java.io.File
import java.util.concurrent.Executors

/** Calls takeScreenshotOfWindow 20 times (API 34+) and logs successes, error codes, min interval. */
object PeekProbe {
    private const val TRIES = 20
    private val executor = Executors.newSingleThreadExecutor()

    fun run(service: AccessibilityService, log: File, outDir: File) {
        if (Build.VERSION.SDK_INT < 34) {
            log.appendText("{\"result\":\"unavailable\",\"sdk\":${Build.VERSION.SDK_INT}}\n")
            return
        }
        val windowId = service.windows.firstOrNull { it.isActive }?.id
        if (windowId == null) {
            log.appendText("{\"result\":\"noActiveWindow\"}\n")
            return
        }
        val stamps = ArrayList<Long>()
        var ok = 0
        var saved = false
        val errors = ArrayList<Int>()
        fun finish() {
            val gaps = stamps.zipWithNext { a, b -> b - a }
            log.appendText(
                "{\"result\":\"done\",\"ok\":$ok,\"errors\":$errors,\"minIntervalMs\":${gaps.minOrNull() ?: -1}," +
                    "\"savedPng\":$saved}\n"
            )
        }
        var n = 0
        lateinit var next: () -> Unit
        next = {
            if (n >= TRIES) {
                finish()
            } else {
                n++
                service.takeScreenshotOfWindow(
                    windowId,
                    executor,
                    object : AccessibilityService.TakeScreenshotCallback {
                        override fun onSuccess(result: AccessibilityService.ScreenshotResult) {
                            ok++
                            stamps.add(SystemClock.uptimeMillis())
                            if (!saved) {
                                val hw = result.hardwareBuffer
                                Bitmap.wrapHardwareBuffer(hw, result.colorSpace)?.let { b ->
                                    File(outDir, "peek.png").outputStream().use {
                                        b.compress(Bitmap.CompressFormat.PNG, 100, it)
                                    }
                                    saved = true
                                }
                                hw.close()
                            }
                            next()
                        }

                        override fun onFailure(errorCode: Int) {
                            errors.add(errorCode)
                            next()
                        }
                    }
                )
            }
        }
        next()
    }
}
