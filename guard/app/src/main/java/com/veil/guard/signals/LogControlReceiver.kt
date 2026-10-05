package com.veil.guard.signals

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log

/** adb shell am broadcast -a com.veil.guard.LOG -n com.veil.guard/.signals.LogControlReceiver --es cmd start|stop --es name s */
class LogControlReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val logger = EventLogger.instance
        if (logger == null) {
            Log.w("VeilSignals", "VEIL_LOG service not connected")
            return
        }
        when (intent.getStringExtra("cmd")) {
            "start" -> logger.start(
                intent.getStringExtra("name") ?: "log",
                SignalsHub.snapshotter as? BoundedSnapshotter
            )

            "stop" -> logger.stop()
        }
    }
}
