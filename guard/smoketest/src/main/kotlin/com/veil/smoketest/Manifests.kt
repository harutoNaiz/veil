package com.veil.smoketest

import com.veil.runtime.IoSpec
import com.veil.runtime.ModelSpec
import java.io.File
import org.json.JSONArray
import org.json.JSONObject

/** Reads `models.txt` lines `id|file.onnx|manifest.json` from [dir] (manifest has inputs/outputs). */
object Manifests {
    private fun ios(a: JSONArray): List<IoSpec> = List(a.length()) {
        val o = a.getJSONObject(it)
        val s = o.getJSONArray("shape")
        IoSpec(o.getString("name"), LongArray(s.length()) { i -> s.getLong(i) }, o.optString("dtype", "float32"))
    }

    fun parse(id: String, path: String, manifestJson: String): ModelSpec {
        val j = JSONObject(manifestJson)
        return ModelSpec(id, path, ios(j.getJSONArray("inputs")), ios(j.getJSONArray("outputs")))
    }

    fun loadAll(dir: File): List<ModelSpec> = File(dir, "models.txt").readLines().filter { it.isNotBlank() }.map {
        val (id, file, mani) = it.split("|")
        parse(id, File(dir, "models/$file").path, File(dir, "models/$mani").readText())
    }
}
