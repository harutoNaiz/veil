package com.veil.guard.capture.service

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/**
 * `am broadcast -a com.veil.guard.capture.CMD --es cmd start|pause|resume|stop|source|saveFrames [--es value <v>]`.
 * Exported, protected by android.permission.DUMP (shell/system only). Forwards to CaptureService.
 */
class CaptureCommandReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != ACTION_CMD) return
        val cmd = intent.getStringExtra(EXTRA_CMD) ?: return
        val value = intent.getStringExtra(EXTRA_VALUE)
        val serviceIntent =
            Intent(context, CaptureService::class.java).apply {
                action = ACTION_CMD
                putExtra(EXTRA_CMD, cmd)
                if (value != null) putExtra(EXTRA_VALUE, value)
            }
        context.startForegroundService(serviceIntent)
    }

    companion object {
        const val ACTION_CMD = "com.veil.guard.capture.CMD"
        const val EXTRA_CMD = "cmd"
        const val EXTRA_VALUE = "value"
    }
}
