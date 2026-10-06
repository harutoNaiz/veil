package com.veil.guard.bridge

import android.app.NotificationManager
import android.content.Context
import android.content.Intent
import android.provider.Settings
import com.veil.guard.capture.service.CaptureCommandReceiver
import com.veil.guard.capture.service.CaptureService
import java.io.File
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

/** Maps Console ops onto the Guard's existing command path (CaptureService intents, prefs, files). */
class AndroidBridgeOps(private val ctx: Context) : BridgeOps {
    private val guardPrefs get() = ctx.getSharedPreferences("veil_guard", Context.MODE_PRIVATE)

    private fun wasRunning() =
        ctx.getSharedPreferences("veil.capture", Context.MODE_PRIVATE).getBoolean("wasRunning", false)

    private fun conceptsDir() = File(ctx.externalMediaDirs.first(), "concepts").also { it.mkdirs() }

    private fun cmd(name: String, value: String? = null) {
        val i =
            Intent(ctx, CaptureService::class.java).apply {
                action = CaptureCommandReceiver.ACTION_CMD
                putExtra(CaptureCommandReceiver.EXTRA_CMD, name)
                if (value != null) putExtra(CaptureCommandReceiver.EXTRA_VALUE, value)
            }
        ctx.startForegroundService(i)
    }

    private fun readConcepts() = conceptsDir().listFiles { f -> f.name.endsWith(".json") }.orEmpty().flatMap { f ->
        runCatching {
            val root = Json.parseToJsonElement(f.readText()).jsonObject
            val arr = root["concepts"] as? JsonArray
            (arr?.map { it.jsonObject } ?: listOf(root)).map {
                val id = it["conceptId"]!!.jsonPrimitive.content
                BridgeConcept(id, it["displayName"]?.jsonPrimitive?.content ?: id, true)
            }
        }.getOrDefault(emptyList())
    }

    override fun state(): BridgeState {
        val running = wasRunning()
        if (running) cmd("status") // refreshes files/status.json for the next poll
        val paused =
            runCatching {
                File(ctx.filesDir, "status.json").readText()
            }.getOrDefault("").contains("\"userPaused\":true")
        val a11y =
            Settings.Secure.getString(ctx.contentResolver, Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES)
                .orEmpty()
                .contains(ctx.packageName)
        val notif = ctx.getSystemService(NotificationManager::class.java).areNotificationsEnabled()
        return BridgeState(
            running = running,
            mode = guardPrefs.getString("mode", "balanced") ?: "balanced",
            captureState = if (!running) {
                "stopped"
            } else if (paused) {
                "paused"
            } else {
                "running"
            },
            permissions = mapOf("accessibility" to a11y, "notifications" to notif, "screenCapture" to running),
            skipList = guardPrefs.getString("skip", "").orEmpty().split(',').filter { it.isNotEmpty() },
            concepts = readConcepts(),
            activePackSha256 = null
        )
    }

    override fun start() = cmd("start")

    override fun pause() = cmd("pause")

    override fun resume() = cmd("resume")

    override fun stop() = cmd("stop")

    override fun setMode(mode: String) = cmd("mode", mode)

    override fun setSkipList(packages: List<String>) {
        val csv = packages.joinToString(",")
        guardPrefs.edit().putString("skip", csv).apply()
        cmd("skip", csv)
    }

    override fun installPack(json: String) {
        File(conceptsDir(), "console-pack.json").writeText(json)
        if (wasRunning()) cmd("concepts")
    }

    override fun recentCovers(limit: Int): List<BridgeCover> {
        val f = File(ctx.filesDir, "debug.jsonl")
        if (!f.exists()) return emptyList()
        return BridgeCore.coversFromLog(f.readLines().takeLast(400), limit)
    }
}
