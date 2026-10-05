package com.veil.guard.signals

import android.accessibilityservice.AccessibilityService
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.graphics.Rect
import android.os.Build
import android.os.SystemClock
import android.view.accessibility.AccessibilityEvent
import com.veil.guard.capture.ScreenshotBridge
import java.io.File
import java.util.concurrent.atomic.AtomicLong

/** Phase 4.3 hooks its overlay in here (the one production accessibility service). */
interface OverlayHost {
    fun onServiceConnected(service: AccessibilityService)

    fun onServiceDisconnected()
}

object OverlayHostRegistry {
    @Volatile var host: OverlayHost? = null
}

class GuardAccessibilityService : AccessibilityService() {
    private val ids = AtomicLong(0)
    private val mapper = EventMapper(ScrollTracker())
    private val foreground = ForegroundTracker()
    private var screenReceiver: BroadcastReceiver? = null

    override fun onServiceConnected() {
        EventLogger.instance = EventLogger(File(filesDir, "signals"))
        val shot = A11yScreenshotSource(this)
        SignalsHub.screenshots = shot
        ScreenshotBridge.provider = shot
        SignalsHub.snapshotter =
            BoundedSnapshotter(A11yNode.rootOf(this), SystemClock::uptimeMillis, ids = { ids.getAndIncrement() })
        registerScreenReceiver()
        OverlayHostRegistry.host?.onServiceConnected(this)
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (event == null) return
        val raw = copy(event)
        if (raw.type == EventMapper.TYPE_WINDOW_STATE_CHANGED) {
            SignalsHub.foregroundPackage = foreground.onWindowState(raw.packageName, raw.className)
        }
        emit(mapper.map(raw) { ids.getAndIncrement() })
    }

    @Suppress("DEPRECATION")
    private fun copy(e: AccessibilityEvent): RawEvent {
        var key: String? = null
        var rect: PxRect? = null
        if (e.eventType == AccessibilityEvent.TYPE_VIEW_SCROLLED) {
            // The one allowed node fetch: a single source node, no children, for container bounds and id.
            val src = e.source
            if (src != null) {
                val r = Rect()
                src.getBoundsInScreen(r)
                rect = PxRect(r.left, r.top, r.width(), r.height())
                key = src.viewIdResourceName ?: src.className?.toString()
                src.recycle()
            }
        }
        return RawEvent(
            e.eventType, e.eventTime, e.packageName?.toString(), e.className?.toString(), e.windowId, key, rect,
            e.scrollDeltaX, e.scrollDeltaY, e.scrollX, e.scrollY, e.maxScrollX, e.maxScrollY, e.contentChangeTypes
        )
    }

    private fun emit(event: UiEvent?) {
        if (event != null) EventLogger.instance?.write(event)
    }

    private fun registerScreenReceiver() {
        val r =
            object : BroadcastReceiver() {
                override fun onReceive(context: Context, intent: Intent) {
                    val t = SystemClock.uptimeMillis()
                    val id = ids.getAndIncrement()
                    emit(if (intent.action == Intent.ACTION_SCREEN_OFF) ScreenOff(id, t) else ScreenOn(id, t))
                }
            }
        val f =
            IntentFilter().apply {
                addAction(Intent.ACTION_SCREEN_ON)
                addAction(Intent.ACTION_SCREEN_OFF)
            }
        if (Build.VERSION.SDK_INT >=
            33
        ) {
            registerReceiver(r, f, Context.RECEIVER_NOT_EXPORTED)
        } else {
            registerReceiver(r, f)
        }
        screenReceiver = r
    }

    override fun onInterrupt() {}

    override fun onUnbind(intent: Intent?): Boolean {
        OverlayHostRegistry.host?.onServiceDisconnected()
        screenReceiver?.let { unregisterReceiver(it) }
        screenReceiver = null
        EventLogger.instance?.stop()
        EventLogger.instance = null
        SignalsHub.screenshots = null
        SignalsHub.snapshotter = null
        SignalsHub.foregroundPackage = null
        ScreenshotBridge.provider = null
        return super.onUnbind(intent)
    }
}
