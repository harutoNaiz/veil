package com.veil.guard.capture.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.graphics.drawable.Icon
import com.veil.guard.R

/** The ongoing capture notification, with a "Resume Veil" action when awaiting permission. */
object CaptureNotifications {
    const val CHANNEL_ID = "capture_status"
    const val NOTIFICATION_ID = 4101

    fun ensureChannel(context: Context) {
        val mgr = context.getSystemService(NotificationManager::class.java)
        val channel =
            NotificationChannel(
                CHANNEL_ID,
                context.getString(R.string.capture_channel_name),
                NotificationManager.IMPORTANCE_LOW
            )
        mgr.createNotificationChannel(channel)
    }

    fun build(context: Context, text: String, awaitingPermission: Boolean, reason: String? = null): Notification {
        ensureChannel(context)
        val builder =
            Notification.Builder(context, CHANNEL_ID)
                .setContentTitle(context.getString(R.string.capture_notification_title))
                .setContentText(
                    when (reason) {
                        "restarted" -> context.getString(R.string.capture_text_restarted)
                        "keyguard" -> context.getString(R.string.capture_text_keyguard)
                        else -> text
                    }
                )
                .setOngoing(true)
                .setSmallIcon(android.R.drawable.ic_menu_view)
        if (awaitingPermission) {
            val intent =
                Intent(context, ConsentActivity::class.java).apply {
                    flags = Intent.FLAG_ACTIVITY_NEW_TASK
                }
            val pending =
                PendingIntent.getActivity(
                    context,
                    0,
                    intent,
                    PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
                )
            builder.setContentIntent(pending)
            builder.addAction(
                Notification.Action
                    .Builder(
                        Icon.createWithResource(context, android.R.drawable.ic_menu_view),
                        context.getString(R.string.capture_resume_action),
                        pending
                    ).build()
            )
        }
        return builder.build()
    }
}
