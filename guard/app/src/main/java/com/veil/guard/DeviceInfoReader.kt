package com.veil.guard

import android.app.Activity
import android.app.ActivityManager
import android.content.Context
import android.os.Build

/**
 * Must be called on the main thread (reads Activity.display). Uses Build.SOC_MODEL, Build.SOC_MANUFACTURER,
 * Build.HARDWARE, Build.BOARD, Build.MANUFACTURER, Build.MODEL, Build.VERSION.RELEASE, Build.VERSION.SDK_INT,
 * Build.DISPLAY, ActivityManager.MemoryInfo.totalMem, the display's physical width and height,
 * resources.displayMetrics.densityDpi and the display's supported refresh rates.
 */
fun readDeviceInfo(activity: Activity): DeviceInfo {
    val memoryInfo = ActivityManager.MemoryInfo()
    val activityManager = activity.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
    activityManager.getMemoryInfo(memoryInfo)
    val display = activity.display!!
    val mode = display.mode
    return DeviceInfo(
        socModel = Build.SOC_MODEL,
        socManufacturer = Build.SOC_MANUFACTURER,
        hardware = Build.HARDWARE,
        board = Build.BOARD,
        manufacturer = Build.MANUFACTURER,
        model = Build.MODEL,
        androidRelease = Build.VERSION.RELEASE,
        sdkInt = Build.VERSION.SDK_INT,
        buildDisplay = Build.DISPLAY,
        ramTotalBytes = memoryInfo.totalMem,
        screenWidthPx = mode.physicalWidth,
        screenHeightPx = mode.physicalHeight,
        densityDpi = activity.resources.displayMetrics.densityDpi,
        refreshRatesHz = display.supportedModes.map { it.refreshRate }.distinct().sorted()
    )
}
