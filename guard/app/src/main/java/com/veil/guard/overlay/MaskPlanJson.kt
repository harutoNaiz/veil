package com.veil.guard.overlay

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.long

object MaskPlanJson {
    fun parse(text: String): CoverPlan {
        val o = Json.parseToJsonElement(text).jsonObject
        require(o["contractVersion"]?.jsonPrimitive?.content == "1.0") { "unsupported contractVersion" }
        val covers = o.getValue("masks").jsonArray.map { cover(it.jsonObject) }
        return CoverPlan(
            o.getValue("planId").jsonPrimitive.long,
            o.getValue("tMs").jsonPrimitive.long,
            o.getValue("screenWidth").jsonPrimitive.int,
            o.getValue("screenHeight").jsonPrimitive.int,
            o["rotation"]?.jsonPrimitive?.int ?: 0,
            covers,
            o["reason"]?.jsonPrimitive?.content ?: ""
        )
    }

    private fun cover(m: JsonObject): Cover {
        val r = m.getValue("rect").jsonObject
        val rect = Px(r.i("x"), r.i("y"), r.i("w"), r.i("h"))
        val style = CoverStyle.valueOf(m.getValue("style").jsonPrimitive.content.uppercase())
        return Cover(
            m.i("maskId"),
            rect,
            style,
            m["layer"]?.jsonPrimitive?.int ?: 0,
            m["peekable"]?.jsonPrimitive?.content == "true",
            m["label"]?.jsonPrimitive?.content
        )
    }

    private fun JsonObject.i(k: String) = getValue(k).jsonPrimitive.int
}
