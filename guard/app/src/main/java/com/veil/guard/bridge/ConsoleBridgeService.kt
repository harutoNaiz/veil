package com.veil.guard.bridge

import android.app.Service
import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.HandlerThread
import android.os.IBinder
import android.os.Message
import android.os.Messenger

/**
 * Bound by the Console APK (same signing key; guarded by [PERMISSION], protectionLevel=signature).
 * Message `what=1`, data `req` = JSON; the reply (`what=1`, data `resp`) goes to `replyTo`.
 */
class ConsoleBridgeService : Service() {
    private var thread: HandlerThread? = null
    private var messenger: Messenger? = null

    override fun onCreate() {
        super.onCreate()
        val t = HandlerThread("veil-console-bridge").also { it.start() }
        thread = t
        val core = BridgeCore(AndroidBridgeOps(applicationContext))
        messenger =
            Messenger(
                object : Handler(t.looper) {
                    override fun handleMessage(msg: Message) {
                        val resp = core.handle(msg.data.getString("req").orEmpty())
                        val to = msg.replyTo ?: return
                        runCatching {
                            to.send(Message.obtain(null, 1).apply { data = Bundle().apply { putString("resp", resp) } })
                        }
                    }
                }
            )
    }

    override fun onBind(intent: Intent?): IBinder? = messenger?.binder

    override fun onDestroy() {
        thread?.quitSafely()
        super.onDestroy()
    }

    companion object {
        const val PERMISSION = "com.veil.guard.permission.CONSOLE"
    }
}
