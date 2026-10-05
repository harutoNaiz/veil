package com.veil.conductor

import com.veil.brain.contract.Finding
import com.veil.brain.contract.FrameMeta
import com.veil.brain.contract.Record
import com.veil.brain.contract.Rect
import com.veil.brain.contract.UiEvent
import java.io.File
import java.util.Base64
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.long
import org.junit.Assert.assertTrue
import org.junit.Test

class ReplayParityTest {
    private val dir = File(System.getProperty("veil.tapes"))
    private val params = File(System.getProperty("veil.repo"), "workshop/twin/params.json").readText()

    private fun parse(s: String) = Json.parseToJsonElement(s).jsonObject

    private fun conv(e: JsonElement): Any? = when (e) {
        is JsonNull -> null

        is JsonObject -> e.entries.associate { it.key to conv(it.value) }

        is JsonArray -> e.map { conv(it) }

        is JsonPrimitive ->
            when {
                e.isString -> e.content
                e.booleanOrNull != null -> e.booleanOrNull
                '.' in e.content -> e.content.toDouble()
                else -> e.content.toLong()
            }
    }

    private fun rect(o: JsonObject) = Rect(
        o["x"]!!.jsonPrimitive.int,
        o["y"]!!.jsonPrimitive.int,
        o["w"]!!.jsonPrimitive.int,
        o["h"]!!.jsonPrimitive.int
    )

    private fun finding(o: JsonObject) = Finding(
        o["findingId"]!!.jsonPrimitive.content, o["frameId"]!!.jsonPrimitive.int, o["lookId"]!!.jsonPrimitive.int,
        o["tMs"]!!.jsonPrimitive.long, o["conceptId"]!!.jsonPrimitive.content, o["layer"]!!.jsonPrimitive.int,
        o["decision"]!!.jsonPrimitive.content, o["probability"]!!.jsonPrimitive.content.toDouble(),
        rect(o["rect"]!!.jsonObject), o["scope"]!!.jsonPrimitive.content, o["lane"]!!.jsonPrimitive.content
    )

    private fun iou(a: Rect, b: Rect): Double {
        val ix = maxOf(0, minOf(a.x + a.w, b.x + b.w) - maxOf(a.x, b.x))
        val iy = maxOf(0, minOf(a.y + a.h, b.y + b.h) - maxOf(a.y, b.y))
        val inter = ix.toDouble() * iy
        val u = a.w.toDouble() * a.h + b.w.toDouble() * b.h - inter
        return if (u <= 0) 1.0 else inter / u
    }

    private fun masks(plan: Map<*, *>?): List<Rect> = (plan?.get("masks") as? List<*>).orEmpty().map {
        val r = (it as Map<*, *>)["rect"] as Map<*, *>
        Rect(
            (r["x"] as Number).toInt(),
            (r["y"] as Number).toInt(),
            (r["w"] as Number).toInt(),
            (r["h"] as Number).toInt()
        )
    }

    private fun tape(meta: JsonObject) {
        val name = meta["name"]!!.jsonPrimitive.content
        val mode = meta["mode"]!!.jsonPrimitive.content
        val frames = ArrayList<Frame>()
        val events = ArrayList<UiEvent>()
        val fRecs = ArrayList<Record>()
        val byFrame = HashMap<Int, ArrayList<Finding>>()
        var h: JsonObject? = null
        for (line in File(dir, meta["tapeIn"]!!.jsonPrimitive.content).readLines().filter { it.isNotBlank() }) {
            val r = parse(line)
            when (r["kind"]!!.jsonPrimitive.content) {
                "header" -> h = r

                "event" -> {
                    val e = r["event"]!!.jsonObject
                    @Suppress("UNCHECKED_CAST")
                    events.add(
                        UiEvent(
                            e["type"]!!.jsonPrimitive.content,
                            e["tMs"]!!.jsonPrimitive.long,
                            e["dx"]?.jsonPrimitive?.int ?: 0,
                            e["dy"]?.jsonPrimitive?.int ?: 0,
                            e["packageName"]?.takeIf {
                                it !is JsonNull
                            }?.jsonPrimitive?.content,
                            conv(e) as Map<String, Any?>
                        )
                    )
                }

                "finding" -> {
                    val fo = r["finding"]!!.jsonObject
                    fRecs.add(linkedMapOf("tMs" to r["tMs"]!!.jsonPrimitive.long, "finding" to conv(fo)))
                    byFrame.getOrPut(fo["frameId"]!!.jsonPrimitive.int) { ArrayList() }.add(finding(fo))
                }

                "frame" -> {
                    val own = (r["ownOverlay"]?.jsonArray ?: JsonArray(emptyList())).map { rect(it.jsonObject) }
                    val hh = h!!
                    val fm =
                        FrameMeta(
                            r["frameId"]!!.jsonPrimitive.int,
                            r["tMs"]!!.jsonPrimitive.long,
                            hh["width"]!!.jsonPrimitive.int,
                            hh["height"]!!.jsonPrimitive.int,
                            hh["screenWidth"]!!.jsonPrimitive.int,
                            hh["screenHeight"]!!.jsonPrimitive.int,
                            own
                        )
                    frames.add(Frame(fm, Base64.getDecoder().decode(r["thumb"]!!.jsonPrimitive.content)))
                }
            }
        }
        val worker = ManualWorker(alwaysFree = true)
        val overlay = RecordingOverlay()
        val c =
            Conductor(
                mode, params, listOf(ScriptedLane(byFrame)), worker, overlay, {},
                { if (it["kind"] == "look") worker.tag = (it["frameId"] as Number).toInt() }, Counters(), emptySet(),
                { emptyList() }
            )
        val delivered = HashSet<Int>()
        var direct = 0
        Replay.run(c, frames.asSequence(), events, fRecs) { rec ->
            @Suppress("UNCHECKED_CAST")
            val fo = rec["finding"] as Map<String, Any?>
            val fid = (fo["frameId"] as Number).toInt()
            val p = worker.pending.firstOrNull { it.tag == fid }
            if (p != null) {
                worker.complete(p)
                delivered.add(fid)
            } else if (fid !in delivered) {
                direct++
                c.inject(fo)
            }
        }
        val got = overlay.plans.associateBy { (it["basedOnFrameId"] as Number).toInt() }
        var total = 0
        var ok = 0
        for (line in File(dir, meta["tapeOut"]!!.jsonPrimitive.content).readLines().filter { it.isNotBlank() }) {
            val r = parse(line)
            if (r["kind"]!!.jsonPrimitive.content != "maskPlan") continue
            val mine = masks(got[r["frameId"]!!.jsonPrimitive.int])
            for (m in masks(conv(r["plan"]!!) as Map<*, *>)) {
                total++
                if (mine.any { iou(it, m) >= 0.9 }) ok++
            }
        }
        val pct = if (total == 0) 100.0 else 100.0 * ok / total
        println("PARITY $name masks=$total matched=${"%.1f".format(pct)}% direct=$direct")
        assertTrue("$name parity $pct", pct >= 95.0)
    }

    @Test fun goldenTapes() {
        val metas = parse(File(dir, "tapes.json").readText())["tapes"]!!.jsonArray.map { it.jsonObject }
        for (m in metas) tape(m)
        if (!File(System.getProperty("veil.repo"), "data/ch2/synth-test").exists()) println("SKIP synth")
    }
}
