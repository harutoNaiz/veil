package com.veil.guard.replay

import android.app.Activity
import android.graphics.Bitmap
import android.media.MediaMetadataRetriever
import android.os.Bundle
import com.veil.brain.contract.Finding
import com.veil.brain.contract.FrameMeta
import com.veil.brain.contract.Record
import com.veil.brain.contract.Rect
import com.veil.brain.contract.UiEvent
import com.veil.conductor.AiWorker
import com.veil.conductor.Conductor
import com.veil.conductor.Counters
import com.veil.conductor.Frame
import com.veil.conductor.Lane
import com.veil.conductor.OverlayPort
import com.veil.conductor.Replay
import com.veil.conductor.Thumbs
import java.io.File
import org.json.JSONObject

/** Debug-only: replays a recorded video + events + findings through the Conductor; writes files/replay/plans.jsonl. */
class ReplayActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val dir = File("/sdcard/Android/media/com.veil.guard/replay/")
        val video = File(dir, intent.getStringExtra("video") ?: "video.mp4")
        val events = File(dir, intent.getStringExtra("events") ?: "events.jsonl")
        val findings = File(dir, intent.getStringExtra("findings") ?: "findings.jsonl")
        val params = File(dir, "params.json").readText()
        val mode = intent.getStringExtra("mode") ?: "balanced"
        val out = File(filesDir, "replay").apply { mkdirs() }
        Thread {
            run(video, events, findings, params, mode, File(out, "plans.jsonl"))
            finish()
        }.start()
    }

    private fun run(video: File, events: File, findings: File, params: String, mode: String, out: File) {
        val dm = resources.displayMetrics
        val evs = ArrayList<UiEvent>()
        val frecs = ArrayList<Record>()
        val byFrame = HashMap<Int, ArrayList<Finding>>()
        for (l in events.readLines().filter { it.isNotBlank() }) {
            val e = JSONObject(l).let { it.optJSONObject("event") ?: it }
            val pkg = if (e.isNull("packageName")) null else e.optString("packageName")
            evs.add(UiEvent(e.getString("type"), e.getLong("tMs"), e.optInt("dx"), e.optInt("dy"), pkg))
        }
        for (l in findings.readLines().filter { it.isNotBlank() }) {
            val r = JSONObject(l)
            val f = r.getJSONObject("finding")
            val rc = f.getJSONObject("rect")
            val fd =
                Finding(
                    f.getString("findingId"), f.getInt("frameId"), f.getInt("lookId"), f.getLong("tMs"),
                    f.getString("conceptId"), f.getInt("layer"), f.getString("decision"), f.getDouble("probability"),
                    Rect(rc.getInt("x"), rc.getInt("y"), rc.getInt("w"), rc.getInt("h")), f.getString("scope"),
                    f.getString("lane")
                )
            byFrame.getOrPut(fd.frameId) { ArrayList() }.add(fd)
            frecs.add(linkedMapOf("tMs" to r.getLong("tMs"), "finding" to jsonToMap(f)))
        }
        val lane = Lane { byFrame[it.frame.meta.frameId] ?: emptyList() }
        val worker =
            object : AiWorker {
                @Volatile override var busy = false

                override fun submit(job: () -> List<Finding>, done: (List<Finding>, Long) -> Unit) {
                    busy = true
                    Thread {
                        val t0 = System.nanoTime()
                        val r = job()
                        busy = false
                        done(r, (System.nanoTime() - t0) / 1_000_000)
                    }.start()
                }
            }
        val noop =
            object : OverlayPort {
                override fun submit(plan: Record) = Unit

                override fun shift(dx: Int, dy: Int, tMs: Long) = Unit
            }
        val c = Conductor(mode, params, listOf(lane), worker, noop, {}, {}, Counters(), emptySet(), { emptyList() })
        val mmr = MediaMetadataRetriever().apply { setDataSource(video.path) }
        val n = mmr.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_FRAME_COUNT)!!.toInt()
        val durMs = mmr.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)!!.toLong()
        val fps = n * 1000.0 / durMs
        val seq =
            (0 until n).asSequence().map { i ->
                val src = mmr.getFrameAtIndex(i)!!
                val w = 360
                val h = src.height * w / src.width
                val bmp = Bitmap.createScaledBitmap(src, w, h, true)
                val px = IntArray(w * h)
                bmp.getPixels(px, 0, w, 0, 0, w, h)
                val tMs = (i * 1000 / fps).toLong() + 1000
                val meta = FrameMeta(i, tMs, w, h, dm.widthPixels, dm.heightPixels, emptyList())
                Frame(meta, Thumbs.fromArgb(px, w, h), px)
            }
        Replay.run(c, seq, evs, frecs, out)
        mmr.release()
    }

    private fun jsonToMap(o: JSONObject): Record {
        val m = LinkedHashMap<String, Any?>()
        for (k in o.keys()) {
            val v = o.get(k)
            m[k] = if (v is JSONObject) {
                jsonToMap(v)
            } else if (v == JSONObject.NULL) {
                null
            } else {
                v
            }
        }
        return m
    }
}
