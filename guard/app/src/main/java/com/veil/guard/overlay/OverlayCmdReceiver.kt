package com.veil.guard.overlay

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log

class OverlayCmdReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val value = intent.getStringExtra("value")
        when (val cmd = intent.getStringExtra("cmd")) {
            "plan" -> {
                val plan =
                    runCatching { MaskPlanJson.parse(value ?: "") }
                        .onFailure { Log.w("VeilOverlay", "bad plan: ${it.message}") }
                        .getOrNull()
                if (plan != null) OverlayHub.sink?.submit(plan)
            }

            null -> Unit

            else -> OverlayCommands.handlers[cmd]?.invoke(value)
        }
    }
}
