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
import com.veil.guard.overlay.OverlayCommands
import com.veil.guard.overlay.OverlayRenderer
import com.veil.guard.overlay.glue.GlueController
import com.veil.guard.overlay.self.SelfCapture
import com.veil.guard.overlay.touch.CoverTouchLayer
import com.veil.guard.wire.EventAdapter
import com.veil.guard.wire.LayoutFeed
import com.veil.guard.wire.LiveOverlay
import com.veil.guard.wire.WireHub
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
    private val ownActivities: Set<String> by lazy {
        try {
            val flags = android.content.pm.PackageManager.GET_ACTIVITIES
            packageManager.getPackageInfo(packageName, flags).activities?.map { it.name }?.toSet() ?: emptySet()
        } catch (e: Exception) {
            emptySet()
        }
    }
    private val mapper =
        EventMapper(ScrollTracker(), "com.veil.guard") { cn -> cn != null && cn in ownActivities }
    private val foreground = ForegroundTracker()
    private var screenReceiver: BroadcastReceiver? = null
    private var glue: GlueController? = null
    private var touch: CoverTouchLayer? = null
    private var liveOverlay: LiveOverlay? = null
    private val layoutFeed = LayoutFeed()

    override fun onServiceConnected() {
        EventLogger.instance = EventLogger(File(filesDir, "signals"))
        val shot = A11yScreenshotSource(this)
        SignalsHub.screenshots = shot
        ScreenshotBridge.provider = shot
        SignalsHub.snapshotter =
            BoundedSnapshotter(A11yNode.rootOf(this), SystemClock::uptimeMillis, ids = { ids.getAndIncrement() })
        registerScreenReceiver()
        if (OverlayHostRegistry.host == null) OverlayHostRegistry.host = OverlayRenderer()
        OverlayHostRegistry.host?.onServiceConnected(this)
        SelfCapture.install(this)
        OverlayCommands.handlers["selfcap"]?.invoke("on")
        val b = windowManager().currentWindowMetrics.bounds
        glue = GlueController(File(filesDir, "overlay"), b.width(), b.height()).also { it.register() }
        val t = CoverTouchLayer(this, File(filesDir, "overlay/touch.jsonl"))
        touch = t
        liveOverlay = LiveOverlay(t)
        WireHub.overlay = liveOverlay
        WireHub.layout = layoutFeed::latest
        // Reboot / update / crash: the system rebinds this service; resume protection if the user left it on.
        if (com.veil.guard.app.VeilSettings.protectionOn(this)) {
            runCatching {
                startForegroundService(
                    android.content.Intent(this, com.veil.guard.capture.service.CaptureService::class.java).apply {
                        action = com.veil.guard.capture.service.CaptureCommandReceiver.ACTION_CMD
                        putExtra(com.veil.guard.capture.service.CaptureCommandReceiver.EXTRA_CMD, "source")
                        putExtra(com.veil.guard.capture.service.CaptureCommandReceiver.EXTRA_VALUE, "a11y")
                    }
                )
            }
        }
    }

    private fun windowManager() = getSystemService(android.view.WindowManager::class.java)

    /** A window-state event counts as an app switch only when it comes from an application window. */
    private fun isAppSwitch(e: AccessibilityEvent): Boolean {
        val w = runCatching { windows.firstOrNull { it.id == e.windowId } }.getOrNull()
        if (w != null) return w.type == android.view.accessibility.AccessibilityWindowInfo.TYPE_APPLICATION
        val p = e.packageName?.toString() ?: return false
        return p != "com.android.systemui" && !p.contains("inputmethod")
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (event == null) return
        val raw = copy(event)
        if (raw.type == EventMapper.TYPE_WINDOW_STATE_CHANGED) {
            SignalsHub.foregroundPackage = foreground.onWindowState(raw.packageName, raw.className)
            // Status bar, notifications, keyboard, gesture bars, popups: not the user switching apps. Forwarding
            // them made the brain clear every tracked object, so most covers never got confirmed.
            if (!isAppSwitch(event)) return
        }
        if (raw.type == AccessibilityEvent.TYPE_VIEW_SCROLLED) {
            glue?.onEvent(raw)
            (OverlayHostRegistry.host as? OverlayRenderer)?.onScrollEvent(raw)
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
        if (event == null) return
        EventLogger.instance?.write(event)
        EventAdapter.toBrain(event)?.let { WireHub.events?.invoke(it) }
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
        WireHub.overlay = null
        WireHub.layout = { emptyList() }
        liveOverlay?.close()
        liveOverlay = null
        touch?.clear()
        touch = null
        SelfCapture.uninstall()
        OverlayCommands.handlers.remove("glue")
        glue = null
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
