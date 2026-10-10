package com.veil.guard.capture.service

import android.app.Activity
import android.app.NotificationManager
import android.app.Service
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.ServiceInfo
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.PowerManager
import android.os.SystemClock
import android.view.WindowManager
import com.veil.guard.capture.CaptureLog
import com.veil.guard.capture.CaptureState
import com.veil.guard.capture.CoverMath
import com.veil.guard.capture.FrameSize
import com.veil.guard.capture.FrameSource
import com.veil.guard.capture.OwnCoverBridge
import com.veil.guard.capture.PxRect
import com.veil.guard.capture.backup.AccessibilityScreenSource
import com.veil.guard.capture.source.MediaProjectionScreenSource
import com.veil.guard.capture.state.CaptureEvent
import com.veil.guard.capture.state.CaptureStateMachine
import com.veil.guard.overlay.self.SelfCapture
import com.veil.guard.wire.FrameAdapter
import com.veil.guard.wire.GuardRuntime
import com.veil.guard.wire.WireHub

/**
 * FGS (foregroundServiceType="mediaProjection") holding the MediaProjection token and driving
 * [CaptureStateMachine]. `source` swaps the active [FrameSource] at runtime (owned by 4.1.2/4.1.3).
 */
class CaptureService : Service() {
    private val stateMachine = CaptureStateMachine()
    private var projection: MediaProjection? = null
    private var captureLog: CaptureLog? = null
    private var source: FrameSource? = null
    private val mainHandler = Handler(Looper.getMainLooper())
    private var autoFallback = true

    private fun clog(what: String, detail: String) {
        val rec = linkedMapOf<String, Any?>("kind" to "capture", "tMs" to SystemClock.uptimeMillis())
        rec["what"] = what
        rec["detail"] = detail
        (source as? MediaProjectionScreenSource)?.let { rec["sinceFrameMs"] = it.sinceLastFrameMs() }
        WireHub.log?.write(rec)
    }

    private val screenOffReceiver =
        object : BroadcastReceiver() {
            override fun onReceive(context: Context, intent: Intent) {
                clog("screen", intent.action.orEmpty())
                if (intent.action == Intent.ACTION_SCREEN_OFF) {
                    handleEvent(CaptureEvent.KeyguardLocked)
                }
            }
        }

    private val projectionCallback =
        object : MediaProjection.Callback() {
            override fun onStop() {
                clog("projection", "onStop")
                projection = null
                handleEvent(CaptureEvent.ProjectionStopped(cause = "stopped"))
            }

            override fun onCapturedContentResize(width: Int, height: Int) {
                clog("projection", "contentResize ${width}x$height")
                handleEvent(CaptureEvent.ContentResized(FrameSize(width, height), displaySize()))
            }

            override fun onCapturedContentVisibilityChanged(isVisible: Boolean) {
                clog("projection", "contentVisible=$isVisible")
            }
        }

    override fun onCreate() {
        super.onCreate()
        captureLog = CaptureLog(this)
        OwnCoverBridge.coverage = {
            val rects = SelfCapture.current?.at(SystemClock.uptimeMillis()).orEmpty()
            val s = displaySize()
            CoverMath.fraction(rects.map { PxRect(it.x, it.y, it.w, it.h) }, s.width, s.height)
        }
        registerReceiver(
            screenOffReceiver,
            IntentFilter(Intent.ACTION_SCREEN_OFF).apply { addAction(Intent.ACTION_SCREEN_ON) }
        )
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val action = intent?.action
        val consentOk =
            action == ACTION_CONSENT_RESULT &&
                intent.getIntExtra(EXTRA_RESULT_CODE, Activity.RESULT_CANCELED) == Activity.RESULT_OK
        val wasRunning = getSharedPreferences(PREFS, Context.MODE_PRIVATE).getBoolean(KEY_WAS_RUNNING, false)
        val decision = RecoveryPolicy.onStart(action, consentOk, projection != null, wasRunning)
        postNotification(decision.fgs)
        decision.event?.let { handleEvent(it) }
        if (decision.stopSelf) {
            stopSelf()
            return START_NOT_STICKY
        }
        when (action) {
            ACTION_CONSENT_RESULT -> onConsentResult(intent!!)
            CaptureCommandReceiver.ACTION_CMD -> onCommand(intent!!)
        }
        return START_STICKY
    }

    override fun onDestroy() {
        runCatching { unregisterReceiver(screenOffReceiver) }
        projection?.unregisterCallback(projectionCallback)
        projection?.stop()
        source?.stop()
        GuardRuntime.stop()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun onConsentResult(intent: Intent) {
        val resultCode = intent.getIntExtra(EXTRA_RESULT_CODE, Activity.RESULT_CANCELED)
        val data =
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                intent.getParcelableExtra(EXTRA_RESULT_DATA, Intent::class.java)
            } else {
                @Suppress("DEPRECATION")
                intent.getParcelableExtra(EXTRA_RESULT_DATA)
            }
        if (resultCode == Activity.RESULT_OK && data != null) {
            val manager = getSystemService(MediaProjectionManager::class.java)
            val proj = manager.getMediaProjection(resultCode, data)
            if (proj != null) {
                proj.registerCallback(projectionCallback, null)
                projection = proj
                handleEvent(CaptureEvent.ConsentGranted(entireScreen = true))
                GuardRuntime.start(applicationContext)
                useSource("mp")
            } else {
                handleEvent(CaptureEvent.ConsentDenied)
            }
        } else {
            handleEvent(CaptureEvent.ConsentDenied)
        }
    }

    private fun onCommand(intent: Intent) {
        when (intent.getStringExtra(CaptureCommandReceiver.EXTRA_CMD)) {
            "pause" -> {
                clog("cmd", "pause")
                handleEvent(CaptureEvent.Pause)
                source?.pause()
                GuardRuntime.pause()
            }

            "resume" -> {
                clog("cmd", "resume")
                handleEvent(CaptureEvent.Resume)
                source?.resume()
                GuardRuntime.resume()
            }

            "stop" -> {
                handleEvent(CaptureEvent.UserStop)
                source?.stop()
                GuardRuntime.stop()
                stopSelf()
            }

            "start" -> {
                val activityIntent =
                    Intent(this, ConsentActivity::class.java).apply {
                        flags = Intent.FLAG_ACTIVITY_NEW_TASK
                    }
                startActivity(activityIntent)
            }

            "source" -> useSource(intent.getStringExtra(CaptureCommandReceiver.EXTRA_VALUE) ?: "mp")

            "mode" -> {
                val m = intent.getStringExtra(CaptureCommandReceiver.EXTRA_VALUE)
                if (m in setOf("light", "balanced", "strict", "off")) {
                    GuardRuntime.setMode(m!!)
                    GuardRuntime.writeStatus(applicationContext)
                }
            }

            "skip" -> {
                val v = intent.getStringExtra(CaptureCommandReceiver.EXTRA_VALUE).orEmpty()
                GuardRuntime.setSkipApps(v.split(',').map { it.trim() }.filter { it.isNotEmpty() }.toSet())
            }

            "concepts" -> GuardRuntime.reloadLanes()

            // mprecover reattach|nudge|recreate|dump on the live MP source; reconsent drops the projection
            // and re-opens the consent dialog; autofallback on|off toggles the automatic switch to a11y.
            "mprecover" -> {
                when (val v = intent.getStringExtra(CaptureCommandReceiver.EXTRA_VALUE).orEmpty()) {
                    "reconsent" -> reconsent()
                    else -> (source as? MediaProjectionScreenSource)?.recover(v) ?: clog("mprecover", "no mp source")
                }
            }

            "autofallback" -> {
                autoFallback = intent.getStringExtra(CaptureCommandReceiver.EXTRA_VALUE) != "off"
                clog("autofallback", autoFallback.toString())
            }

            "saveFrames" -> com.veil.guard.wire.LatestFrame.save(java.io.File(externalMediaDirs.first(), "frame.png"))

            "status" -> GuardRuntime.writeStatus(applicationContext)
        }
    }

    private fun onProjectionDead(why: String) {
        clog("projection-dead", why)
        if (!autoFallback || source !is MediaProjectionScreenSource) return
        clog("fallback", "switching to a11y source")
        useSource("a11y")
    }

    /** Explicit fallback: drop the (silent) projection and ask for consent again. */
    private fun reconsent() {
        clog("reconsent", "dropping projection")
        projection?.unregisterCallback(projectionCallback)
        source?.stop()
        source = null
        projection?.stop()
        projection = null
        handleEvent(CaptureEvent.ProjectionStopped(cause = "reconsent"))
        startActivity(Intent(this, ConsentActivity::class.java).apply { flags = Intent.FLAG_ACTIVITY_NEW_TASK })
    }

    private fun useSource(kind: String) {
        clog("source", kind)
        source?.stop()
        source = null
        val wm = getSystemService(WindowManager::class.java)
        val rotation = wm.defaultDisplay.rotation
        val size = displaySize()
        if (kind == "a11y") {
            GuardRuntime.start(applicationContext)
            source = AccessibilityScreenSource(screen = size, rotation = rotation).also { it.start(FrameAdapter.sink) }
        } else {
            val proj = projection ?: return
            source =
                MediaProjectionScreenSource(
                    proj,
                    size,
                    resources.displayMetrics.densityDpi,
                    rotation,
                    isScreenOn = { getSystemService(PowerManager::class.java).isInteractive },
                    onDead = { why -> mainHandler.post { onProjectionDead(why) } },
                    coverage = OwnCoverBridge.coverage
                )
                    .also { it.start(FrameAdapter.sink) }
        }
    }

    private fun handleEvent(e: CaptureEvent) {
        val t = stateMachine.on(e, System.currentTimeMillis()) ?: return
        captureLog?.appendState(
            "{\"tMs\":${t.tMs},\"state\":\"${t.state.wire}\"," +
                "\"reason\":${t.reason?.let { "\"$it\"" } ?: "null"}}"
        )
        getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putBoolean(KEY_WAS_RUNNING, RecoveryPolicy.wasRunning(t.state))
            .apply()
        postNotification(if (projection != null) FgsKind.PROJECTION else FgsKind.WAITING)
    }

    private fun postNotification(kind: FgsKind) {
        val notification =
            CaptureNotifications.build(
                this,
                stateMachine.state.wire,
                stateMachine.state == CaptureState.AWAITING_PERMISSION,
                stateMachine.reason
            )
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            startForeground(
                CaptureNotifications.NOTIFICATION_ID,
                notification,
                if (kind == FgsKind.PROJECTION) {
                    ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION
                } else {
                    ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE
                }
            )
        } else {
            startForeground(CaptureNotifications.NOTIFICATION_ID, notification)
        }
        getSystemService(NotificationManager::class.java)
            .notify(CaptureNotifications.NOTIFICATION_ID, notification)
    }

    private fun displaySize(): FrameSize {
        val wm = getSystemService(WindowManager::class.java)
        val bounds = wm.currentWindowMetrics.bounds
        return FrameSize(bounds.width(), bounds.height())
    }

    companion object {
        private const val PREFS = "veil.capture"
        private const val KEY_WAS_RUNNING = "wasRunning"
        const val ACTION_CONSENT_RESULT = "com.veil.guard.capture.CONSENT_RESULT"
        const val EXTRA_RESULT_CODE = "resultCode"
        const val EXTRA_RESULT_DATA = "resultData"
    }
}
