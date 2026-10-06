package com.veil.guard.bridge

import java.security.MessageDigest
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.put

/**
 * Pure request/response mapping for the Console IPC. A request is `{"op":..., ...args}`, a reply is
 * `{"ok":true,"result":...}` or `{"ok":false,"err":"..."}`. Ops: hello getState start pause resume stop
 * setMode setSkipList installPack(json, sha256) recentCovers(limit).
 */
class BridgeCore(private val ops: BridgeOps) {
    fun handle(request: String): String = try {
        val req = Json.parseToJsonElement(request).jsonObject
        ok(dispatch(req))
    } catch (e: IllegalArgumentException) {
        err(e.message ?: "bad request")
    } catch (e: Exception) {
        err("${e.javaClass.simpleName}: ${e.message}")
    }

    private fun dispatch(req: JsonObject): JsonElement {
        val a = { k: String -> req[k]?.jsonPrimitive?.content ?: throw IllegalArgumentException("missing $k") }
        return when (val op = a("op")) {
            "hello" ->
                buildJsonObject {
                    put("protocolVersion", PROTOCOL)
                    put("contractVersion", "1.0")
                }

            "getState" -> stateJson(ops.state())

            "start" -> done { ops.start() }

            "pause" -> done { ops.pause() }

            "resume" -> done { ops.resume() }

            "stop" -> done { ops.stop() }

            "setMode" -> {
                val m = a("mode")
                require(m in MODES) { "bad mode $m" }
                done { ops.setMode(m) }
            }

            "setSkipList" -> {
                val pk = req["packages"]?.jsonArray?.map { it.jsonPrimitive.content } ?: emptyList()
                done { ops.setSkipList(pk) }
            }

            "installPack" -> installPack(a("json"), a("sha256"))

            "recentCovers" ->
                JsonArray(
                    ops.recentCovers(req["limit"]?.jsonPrimitive?.int ?: 20).map {
                        buildJsonObject {
                            put("coverId", it.coverId)
                            put("conceptId", it.conceptId)
                            put("tMs", it.tMs)
                        }
                    }
                )

            else -> throw IllegalArgumentException("unknown op $op")
        }
    }

    private fun installPack(json: String, sha: String): JsonElement {
        if (sha256(json.toByteArray()) != sha) return JsonPrimitive("rejectedChecksum")
        if (runCatching { Json.parseToJsonElement(json).jsonObject }.isFailure) return JsonPrimitive("rejectedInvalid")
        ops.installPack(json)
        return JsonPrimitive("accepted")
    }

    private fun done(f: () -> Unit): JsonElement {
        f()
        return JsonNull
    }

    private fun stateJson(s: BridgeState) = buildJsonObject {
        put("protocolVersion", PROTOCOL)
        put("running", s.running)
        put("mode", s.mode)
        put("captureState", s.captureState)
        put("permissions", JsonObject(s.permissions.mapValues { JsonPrimitive(it.value) }))
        put("skipList", JsonArray(s.skipList.map { JsonPrimitive(it) }))
        put(
            "concepts",
            JsonArray(
                s.concepts.map {
                    buildJsonObject {
                        put("conceptId", it.conceptId)
                        put("displayName", it.displayName)
                        put("enabled", it.enabled)
                    }
                }
            )
        )
        put("activePackSha256", s.activePackSha256?.let { JsonPrimitive(it) } ?: JsonNull)
    }

    private fun ok(r: JsonElement) = JsonObject(mapOf("ok" to JsonPrimitive(true), "result" to r)).toString()

    private fun err(m: String) = JsonObject(mapOf("ok" to JsonPrimitive(false), "err" to JsonPrimitive(m))).toString()

    companion object {
        const val PROTOCOL = 1
        val MODES = setOf("light", "balanced", "strict", "off")

        fun sha256(b: ByteArray): String =
            MessageDigest.getInstance("SHA-256").digest(b).joinToString("") { "%02x".format(it) }

        /** Newest-first covers from `debug.jsonl` plan lines (one cover per mask). */
        fun coversFromLog(lines: List<String>, limit: Int): List<BridgeCover> {
            val out = ArrayList<BridgeCover>()
            for (line in lines.asReversed()) {
                if (out.size >= limit) break
                val o = runCatching { Json.parseToJsonElement(line).jsonObject }.getOrNull() ?: continue
                if (o["kind"]?.jsonPrimitive?.content != "plan") continue
                val t = o["tMs"]?.jsonPrimitive?.content?.toDoubleOrNull()?.toLong() ?: 0L
                for (m in o["masks"] as? JsonArray ?: continue) {
                    val mo = m as? JsonObject ?: continue
                    val id = mo["maskId"]?.jsonPrimitive?.content ?: continue
                    out.add(BridgeCover("$t-$id", "layer${mo["layer"]?.jsonPrimitive?.content ?: "?"}", t))
                    if (out.size >= limit) break
                }
            }
            return out
        }
    }
}
