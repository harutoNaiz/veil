package com.veil.console.bridge

import android.app.Activity
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.ServiceConnection
import android.os.Bundle
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.Message
import android.os.Messenger
import java.io.File
import java.util.concurrent.ConcurrentLinkedQueue
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import org.json.JSONArray
import org.json.JSONObject

/** Real backend: talks to the Guard APK's ConsoleBridgeService (signature permission) over a Messenger. */
class RemoteGuardBackend(activity: Activity) : GuardBackend {
    private val ctx: Context = activity.applicationContext
    private val local = NoGuardBackend(activity)
    private val granted = mutableSetOf<String>()

    @Volatile private var service: Messenger? = null
    private val pending = ConcurrentLinkedQueue<CountDownLatch>()

    @Volatile private var lastResp: String? = null

    @Volatile private var connected = CountDownLatch(1)
    private val reply = Messenger(object : Handler(Looper.getMainLooper()) {
        override fun handleMessage(msg: Message) {
            lastResp = msg.data.getString("resp")
            pending.poll()?.countDown()
        }
    })
    private val conn = object : ServiceConnection {
        override fun onServiceConnected(n: ComponentName, b: IBinder) {
            service = Messenger(b)
            connected.countDown()
        }

        override fun onServiceDisconnected(n: ComponentName) {
            service = null
        }
    }

    private fun fail(msg: String): Nothing = throw FlutterError("guard_unavailable", msg, null)

    @Synchronized
    private fun ensureBound(): Messenger {
        service?.let { return it }
        connected = CountDownLatch(1)
        val i = Intent().setComponent(ComponentName(GUARD, "$GUARD.bridge.ConsoleBridgeService"))
        val ok = try {
            ctx.bindService(i, conn, Context.BIND_AUTO_CREATE)
        } catch (e: SecurityException) {
            false
        }
        if (!ok) fail("Guard app not installed or not signed with the same key")
        if (!connected.await(5, TimeUnit.SECONDS)) fail("Guard bridge did not connect")
        return service ?: fail("Guard bridge disconnected")
    }

    /** One request at a time; Pigeon runs host calls on a serial background thread. */
    @Synchronized
    private fun call(req: JSONObject): Any? {
        val m = ensureBound()
        val latch = CountDownLatch(1)
        pending.add(latch)
        m.send(Message.obtain(null, 1).apply {
            replyTo = reply
            data = Bundle().apply { putString("req", req.toString()) }
        })
        if (!latch.await(8, TimeUnit.SECONDS)) {
            pending.remove(latch)
            fail("Guard did not answer")
        }
        val r = JSONObject(lastResp ?: fail("empty reply"))
        if (!r.optBoolean("ok")) throw FlutterError("guard_error", r.optString("err"), null)
        return r.opt("result")
    }

    private fun op(name: String, vararg kv: Pair<String, Any?>) =
        JSONObject().put("op", name).also { o -> kv.forEach { o.put(it.first, it.second) } }

    override fun hello(): HelloMsg {
        val r = call(op("hello")) as JSONObject
        return HelloMsg(r.getLong("protocolVersion"), r.getString("contractVersion"))
    }

    override fun getState(): StateMsg {
        val r = call(op("getState")) as JSONObject
        val p = r.getJSONObject("permissions")
        val a11y = p.optBoolean("accessibility")
        val perms = mapOf(
            "disclosure" to ("disclosure" in granted),
            "accessibility" to a11y,
            "restrictedSettings" to a11y,
            "screenCapture" to p.optBoolean("screenCapture"),
            "notifications" to p.optBoolean("notifications")
        )
        val cs = r.getJSONArray("concepts")
        val concepts = (0 until cs.length()).map {
            val c = cs.getJSONObject(it)
            ConceptMsg(
                c.getString("conceptId"), c.getString("displayName"), c.optBoolean("enabled", true),
                emptyList(), emptyList(), "blur", emptyList()
            )
        }
        val sk = r.getJSONArray("skipList")
        return StateMsg(
            protocolVersion = r.getLong("protocolVersion"),
            running = r.getBoolean("running"),
            mode = r.getString("mode"),
            captureState = r.getString("captureState"),
            permissions = perms,
            skipList = (0 until sk.length()).map { sk.getString(it) },
            concepts = concepts,
            activePackSha256 = null
        )
    }

    override fun start() {
        call(op("start"))
    }

    override fun stop() {
        call(op("stop"))
    }

    override fun setMode(mode: String) {
        call(op("setMode", "mode" to mode))
    }

    override fun setSkipList(packages: List<String>) {
        call(op("setSkipList", "packages" to JSONArray(packages)))
    }

    override fun installedApps(): List<InstalledAppMsg> {
        val pm = ctx.packageManager
        val q = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER)
        return pm.queryIntentActivities(q, 0)
            .map { InstalledAppMsg(it.activityInfo.packageName, it.loadLabel(pm).toString()) }
            .distinctBy { it.packageName }
            .sortedBy { it.label.lowercase() }
    }

    override fun compilePack(text: String, photos: List<FileRefMsg>) = ConceptMsg(
        conceptId = text.trim().lowercase().replace(Regex("[^a-z0-9]+"), "-").trim('-').ifEmpty { "concept" },
        displayName = text.trim(),
        enabled = true,
        looksLike = listOf(text.trim()),
        butNot = emptyList(),
        coverStyle = "blur",
        examplePhotos = photos
    )

    override fun setConceptPack(pack: FileRefMsg): String {
        val f = File(pack.path)
        if (!f.exists()) return "rejectedInvalid"
        return call(op("installPack", "json" to f.readText(), "sha256" to pack.sha256)) as String
    }

    /** The Guard has no feedback op yet. */
    override fun submitFeedback(coverId: String, kind: String) {}

    override fun recentCovers(limit: Long): List<RecentCoverMsg> {
        val a = call(op("recentCovers", "limit" to limit.toInt())) as JSONArray
        return (0 until a.length()).map {
            val c = a.getJSONObject(it)
            RecentCoverMsg(c.getString("coverId"), c.getString("conceptId"), "", c.getLong("tMs"), null)
        }
    }

    override fun requestPermission(perm: String) {
        when (perm) {
            "disclosure" -> granted.add(perm)
            "screenCapture" -> call(op("start")) // the Guard shows its own consent screen
            else -> local.requestPermission(perm)
        }
    }

    companion object {
        const val GUARD = "com.veil.guard"
    }
}
