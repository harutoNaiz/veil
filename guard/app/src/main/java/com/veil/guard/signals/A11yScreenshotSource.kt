package com.veil.guard.signals

import android.accessibilityservice.AccessibilityService
import android.graphics.Bitmap
import android.graphics.Rect
import android.hardware.HardwareBuffer
import android.os.Build
import android.view.Display
import android.view.WindowManager
import android.view.accessibility.AccessibilityWindowInfo
import com.veil.guard.capture.ScreenshotProvider
import com.veil.guard.capture.backup.A11yDisplayFallback

/** Screenshot path via AccessibilityService.takeScreenshot (about 3 fps, no consent dialog). */
class A11yScreenshotSource(private val service: AccessibilityService) :
    ScreenshotSource,
    ScreenshotProvider {
    override val available: Boolean get() = true

    override fun takeScreenshot(onResult: (ScreenshotResult) -> Unit) {
        service.takeScreenshot(
            Display.DEFAULT_DISPLAY,
            service.mainExecutor,
            object : AccessibilityService.TakeScreenshotCallback {
                override fun onSuccess(result: AccessibilityService.ScreenshotResult) {
                    val bmp = Bitmap.wrapHardwareBuffer(result.hardwareBuffer, result.colorSpace)
                    result.hardwareBuffer.close()
                    onResult(
                        if (bmp !=
                            null
                        ) {
                            ScreenshotResult.Ok(bmp, result.timestamp / 1_000_000)
                        } else {
                            ScreenshotResult.Failed(-1)
                        }
                    )
                }

                override fun onFailure(errorCode: Int) = onResult(ScreenshotResult.Failed(errorCode))
            }
        )
    }

    /**
     * Top app window only (takeScreenshotOfWindow, API 34+): our TYPE_ACCESSIBILITY_OVERLAY covers are not part of it,
     * so Veil still sees the real content under its own covers. Status bar and system windows are absent, which is fine
     * for analysis. Frames must stay screen-size, so unless the window fills the screen (bounds and buffer) this falls
     * back to the full-display [takeScreenshot]. Errors (including "interval too short") are passed up as-is.
     */
    override fun takeAppWindowScreenshot(onResult: (HardwareBuffer?, errorCode: Int) -> Unit) {
        val screen = service.getSystemService(WindowManager::class.java).currentWindowMetrics.bounds
        val id = if (Build.VERSION.SDK_INT >= 34) fullScreenAppWindowId(screen.width(), screen.height()) else null
        if (id == null) {
            takeScreenshot { hb, e -> onResult(hb, if (hb != null) A11yDisplayFallback.CODE else e) }
            return
        }
        service.takeScreenshotOfWindow(
            id,
            service.mainExecutor,
            object : AccessibilityService.TakeScreenshotCallback {
                override fun onSuccess(result: AccessibilityService.ScreenshotResult) {
                    val hb = result.hardwareBuffer
                    if (hb.width == screen.width() && hb.height == screen.height()) {
                        onResult(hb, 0)
                    } else {
                        hb.close()
                        takeScreenshot { b, e -> onResult(b, if (b != null) A11yDisplayFallback.CODE else e) }
                    }
                }

                // Window gone or throttled: report it, the caller already retries / backs off like for takeScreenshot.
                override fun onFailure(errorCode: Int) = onResult(null, errorCode)
            }
        )
    }

    /** Id of the focused (else first) TYPE_APPLICATION window if it fills the screen, else null. */
    private fun fullScreenAppWindowId(screenW: Int, screenH: Int): Int? {
        val apps = service.windows.filter { it.type == AccessibilityWindowInfo.TYPE_APPLICATION }
        val w =
            apps.firstOrNull { it.isFocused } ?: apps.firstOrNull { it.isActive } ?: apps.firstOrNull() ?: return null
        val r = Rect()
        w.getBoundsInScreen(r)
        return if (r.width() == screenW && r.height() == screenH) w.id else null
    }

    /** For 4.1's backup capture path (ScreenshotBridge). */
    override fun takeScreenshot(onResult: (HardwareBuffer?, errorCode: Int) -> Unit) {
        service.takeScreenshot(
            Display.DEFAULT_DISPLAY,
            service.mainExecutor,
            object : AccessibilityService.TakeScreenshotCallback {
                override fun onSuccess(result: AccessibilityService.ScreenshotResult) =
                    onResult(result.hardwareBuffer, 0)

                override fun onFailure(errorCode: Int) = onResult(null, errorCode)
            }
        )
    }
}
