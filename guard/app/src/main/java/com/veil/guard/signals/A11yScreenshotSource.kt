package com.veil.guard.signals

import android.accessibilityservice.AccessibilityService
import android.graphics.Bitmap
import android.hardware.HardwareBuffer
import android.view.Display
import com.veil.guard.capture.ScreenshotProvider

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
