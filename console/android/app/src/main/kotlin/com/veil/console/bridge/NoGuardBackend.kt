package com.veil.console.bridge

import android.app.Activity
import android.content.Intent
import android.media.projection.MediaProjectionManager
import android.net.Uri
import android.provider.Settings
import java.io.File
import java.security.MessageDigest

/** Used until the real Guard exists: hello answers, permissions open real system screens, the rest fails. */
class NoGuardBackend(private val activity: Activity) : GuardBackend {
    private val granted = mutableSetOf<String>()

    private fun unavailable(): Nothing = throw FlutterError("guard_unavailable", "No Guard is installed yet", null)

    override fun hello() = HelloMsg(protocolVersion = 1L, contractVersion = "1.0")

    override fun getState() = StateMsg(
        protocolVersion = 1L,
        running = false,
        mode = "balanced",
        captureState = "stopped",
        permissions = listOf("disclosure", "accessibility", "restrictedSettings", "screenCapture", "notifications")
            .associateWith { it in granted },
        skipList = emptyList(),
        concepts = emptyList(),
        activePackSha256 = null,
    )

    override fun start() = unavailable()
    override fun stop() = unavailable()
    override fun setMode(mode: String) = unavailable()
    override fun setSkipList(packages: List<String>) = unavailable()
    override fun installedApps(): List<InstalledAppMsg> = unavailable()
    override fun compilePack(text: String, photos: List<FileRefMsg>): ConceptMsg = unavailable()
    override fun submitFeedback(coverId: String, kind: String) = unavailable()
    override fun recentCovers(limit: Long): List<RecentCoverMsg> = unavailable()

    override fun setConceptPack(pack: FileRefMsg): String {
        val f = File(pack.path)
        if (!f.exists()) return "rejectedInvalid"
        val sha = MessageDigest.getInstance("SHA-256").digest(f.readBytes()).joinToString("") { "%02x".format(it) }
        if (sha != pack.sha256) return "rejectedChecksum"
        unavailable() // checksum ok, but nobody to hand the pack to yet
    }

    override fun requestPermission(perm: String) {
        val intent = when (perm) {
            "disclosure" -> { granted.add(perm); return }
            "accessibility" -> Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)
            "restrictedSettings" -> Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:${activity.packageName}"))
            "notifications" -> Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS).putExtra(Settings.EXTRA_APP_PACKAGE, activity.packageName)
            "screenCapture" -> (activity.getSystemService(Activity.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager).createScreenCaptureIntent()
            else -> throw FlutterError("bad_permission", perm, null)
        }
        if (perm == "screenCapture") activity.startActivityForResult(intent, 4711) else activity.startActivity(intent)
    }
}
