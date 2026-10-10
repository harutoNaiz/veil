package com.veil.guard.wire.ml.accel

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import ai.onnxruntime.TensorInfo
import android.content.Context
import android.util.Log
import com.veil.brain.contract.FrameMeta
import com.veil.brain.contract.Rect
import com.veil.conductor.Frame
import com.veil.conductor.Piece
import com.veil.conductor.Source
import com.veil.guard.wire.ml.ImagePrep
import com.veil.guard.wire.ml.ModelStore
import com.veil.guard.wire.ml.OrtDescriber
import java.io.File
import java.nio.FloatBuffer
import kotlin.math.sqrt
import org.json.JSONArray
import org.json.JSONObject

/**
 * On-device inference benchmark: ImagePrep cost, then per provider (cpu 4/6 threads, xnnpack, qnn) load time, run time
 * and cosine vs cpu for the SigLIP2 batches and NudeNet, plus an end-to-end 22-piece describe. Results are returned and
 * written to <externalMedia>/bench.json and <filesDir>/bench.json; log tag VEIL_BENCH.
 * Hook: `MlBench.run(ctx)` from any background thread.
 */
object MlBench {
    private const val TAG = "VEIL_BENCH"
    private const val W = 1080
    private const val H = 2400

    private fun ms(f: () -> Unit, n: Int): JSONObject {
        f()
        val t = DoubleArray(n)
        for (i in 0 until n) {
            val s = System.nanoTime()
            f()
            t[i] = (System.nanoTime() - s) / 1e6
        }
        t.sort()
        return JSONObject().put("n", n).put("minMs", t.first()).put("medMs", t[n / 2]).put("maxMs", t.last())
    }

    private fun frame(): Frame {
        val px = IntArray(W * H) { i ->
            val x = i % W
            val y = i / W
            val r = (128 + 127 * Math.sin(x * 0.013 + y * 0.002)).toInt()
            val g = (128 + 127 * Math.sin(y * 0.011 - x * 0.004)).toInt()
            val b = (x * 255 / W) xor (y * 255 / H)
            (0xFF shl 24) or (r shl 16) or (g shl 8) or (b and 255)
        }
        return Frame(FrameMeta(1, 0, W, H, W, H, emptyList()), ByteArray(0), px)
    }

    private fun pieces(n: Int): List<Piece> = List(n) { i ->
        val w = 300 + (i % 4) * 150
        val h = 300 + (i % 3) * 200
        Piece("p$i", Rect((i * 37) % (W - w), (i * 101) % (H - h), w, h), Source.TILE, "image", 1)
    }

    private fun inputFor(shape: LongArray, seed: Int): FloatArray {
        val n = shape.fold(1L) { a, b -> a * b }.toInt()
        val per = (n / shape[0]).toInt()
        return FloatArray(n) { i -> (Math.sin((i % per) * 0.0017 + seed) * 0.8).toFloat() }
    }

    private fun flat(res: OrtSession.Result): FloatArray {
        val t = res.get(0) as OnnxTensor
        val fb = t.floatBuffer
        return FloatArray(fb.remaining()).also { fb.get(it) }
    }

    private fun cosine(a: FloatArray, b: FloatArray): Double {
        var d = 0.0
        var na = 0.0
        var nb = 0.0
        for (i in a.indices) {
            d += a[i].toDouble() * b[i]
            na += a[i].toDouble() * a[i]
            nb += b[i].toDouble() * b[i]
        }
        return d / (sqrt(na) * sqrt(nb) + 1e-12)
    }

    private val models = listOf(
        "siglip2-image-b1.onnx",
        "siglip2-image-b4.onnx",
        "siglip2-image-b16.onnx",
        "nudenet-320n.onnx",
        "nudenet-640m.onnx",
        "yoloe-26s-embed-top100.onnx"
    )

    fun run(ctx: Context, iters: Int = 5): JSONObject {
        Accel.prepareProcess(ctx)
        val env = OrtEnvironment.getEnvironment()
        val dir = File(ctx.externalMediaDirs.first(), "models")
        val out = JSONObject().put(
            "device",
            android.os.Build.MODEL
        ).put("cores", Runtime.getRuntime().availableProcessors())
        val fr = frame()
        val ps = pieces(22)

        val prep = JSONObject()
        val crop = ImagePrep.crop(fr.argb!!, W, H, W, H, Rect(0, 0, W, H))
        prep.put("crop_full", ms({ ImagePrep.crop(fr.argb!!, W, H, W, H, Rect(0, 0, W, H)) }, iters))
        prep.put("letterbox_320_full", ms({ ImagePrep.letterbox(crop, 320) }, iters))
        prep.put("letterbox_640_full", ms({ ImagePrep.letterbox(crop, 640) }, iters))
        val buf = FloatArray(3 * 224 * 224)
        prep.put(
            "piece_224_one",
            ms({
                val c = ImagePrep.crop(fr.argb!!, W, H, W, H, ps[0].rect)
                ImagePrep.chw(ImagePrep.resizeBilinear(c, 224, 224), 0.5f, 0.5f, buf, 0)
            }, iters)
        )
        out.put("prep", prep)
        Log.i(TAG, "prep $prep")

        val configs = listOf(
            Triple("cpu-t4", Accel.Mode.CPU, 4),
            Triple("cpu-t6", Accel.Mode.CPU, 6),
            Triple("xnnpack-t6", Accel.Mode.XNNPACK, 6),
            Triple("qnn", Accel.Mode.QNN, 6)
        )
        val ref = HashMap<String, FloatArray>()
        val results = JSONArray()
        for ((label, mode, threads) in configs) {
            val cfg = JSONObject().put("config", label)
            val per = JSONObject()
            val cacheDir = Accel.qnnDir(ctx)
            val opened = HashMap<Int, OrtSession>()
            for (name in models) {
                if (mode == Accel.Mode.QNN && name == "siglip2-image-b16.onnx") {
                    per.put(name, "skipped under qnn (13 min compile; b4 x N is as fast)")
                    continue
                }
                val f = File(dir, name)
                if (!f.isFile) {
                    per.put(name, "missing")
                    continue
                }
                val r = JSONObject()
                try {
                    val t0 = System.nanoTime()
                    var o = Accel.open(env, f, mode, threads, cacheDir)
                    r.put("loadMs", (System.nanoTime() - t0) / 1_000_000).put("ep", o.ep).put("ctxReused", o.cached)
                    if (mode == Accel.Mode.QNN && o.ep == "qnn-htp") {
                        // second load of the same model: what every later start pays (compiled context reused)
                        o.session.close()
                        val t1 = System.nanoTime()
                        o = Accel.open(env, f, mode, threads, cacheDir)
                        r.put("loadMs2", (System.nanoTime() - t1) / 1_000_000).put("ctxReused2", o.cached)
                    }
                    val tensors = ArrayList<OnnxTensor>()
                    try {
                        val feeds = HashMap<String, OnnxTensor>()
                        for ((iname, info) in o.session.inputInfo) {
                            val shape = (info.info as TensorInfo).shape.map { if (it <= 0) 1L else it }.toLongArray()
                            val t = OnnxTensor.createTensor(env, FloatBuffer.wrap(inputFor(shape, 1)), shape)
                            tensors += t
                            feeds[iname] = t
                        }
                        var last = FloatArray(0)
                        r.put("run", ms({ o.session.run(feeds).use { last = flat(it) } }, iters))
                        if (label ==
                            "cpu-t4"
                        ) {
                            ref[name] = last
                        } else {
                            ref[name]?.let { r.put("cosineVsCpu", cosine(it, last)) }
                        }
                    } finally {
                        tensors.forEach { it.close() }
                    }
                    val b = name.removePrefix("siglip2-image-b").removeSuffix(".onnx").toIntOrNull()
                    if (b != null) opened[b] = o.session else o.session.close()
                } catch (t: Throwable) {
                    r.put("error", "${t.javaClass.simpleName}: ${t.message}")
                    Log.w(TAG, "$label $name failed", t)
                }
                per.put(name, r)
            }
            if (opened.isNotEmpty()) {
                try {
                    val d = OrtDescriber(env, opened)
                    cfg.put("describe22", ms({ d.describe(fr, ps) }, iters))
                    if (opened.size > 1) {
                        val only16 = opened[16]?.let { OrtDescriber(env, mapOf(16 to it)) }
                        if (only16 != null) cfg.put("describe22_b16only", ms({ only16.describe(fr, ps) }, iters))
                    }
                } catch (t: Throwable) {
                    cfg.put("describeError", "${t.javaClass.simpleName}: ${t.message}")
                }
            }
            opened.values.forEach { runCatching { it.close() } }
            cfg.put("models", per)
            results.put(cfg)
            Log.i(TAG, cfg.toString())
        }
        out.put("results", results)
        val text = out.toString(2)
        runCatching { File(ctx.filesDir, "bench.json").writeText(text) }
        runCatching { File(ctx.externalMediaDirs.first(), "bench.json").writeText(text) }
        Log.i(TAG, "done " + text.length)
        return out
    }

    /** Convenience for callers that already hold a ModelStore (keeps the shared cache untouched). */
    fun epSummary(store: ModelStore, names: List<String>): String =
        names.joinToString(",") { it + "=" + (store.ep(it) ?: "-") }
}
