package com.veil.guard.wire

import com.veil.brain.contract.Record
import com.veil.guard.overlay.Cover
import com.veil.guard.overlay.CoverPlan
import com.veil.guard.overlay.CoverStyle
import com.veil.guard.overlay.Px

object PlanRecords {
    private fun num(x: Any?): Int = (x as Number).toInt()

    private fun numL(x: Any?): Long = (x as Number).toLong()

    fun toCoverPlan(plan: Record): CoverPlan {
        val masks = (plan["masks"] as? List<*>).orEmpty().map { m ->
            @Suppress("UNCHECKED_CAST")
            val mm = m as Map<String, Any?>

            @Suppress("UNCHECKED_CAST")
            val r = mm["rect"] as Map<String, Any?>
            Cover(
                num(mm["maskId"]),
                Px(num(r["x"]), num(r["y"]), num(r["w"]), num(r["h"])),
                CoverStyle.valueOf(mm["style"].toString().uppercase()),
                (mm["layer"] as? Number)?.toInt() ?: 0,
                mm["peekable"] == true,
                mm["label"] as? String,
                (mm["conceptIds"] as? List<*>).orEmpty().map { it.toString() }
            )
        }
        return CoverPlan(
            numL(plan["planId"]),
            numL(plan["tMs"]),
            num(plan["screenWidth"]),
            num(plan["screenHeight"]),
            (plan["rotation"] as? Number)?.toInt() ?: 0,
            masks,
            plan["reason"]?.toString() ?: ""
        )
    }

    fun shifted(p: CoverPlan, dx: Int, dy: Int): CoverPlan =
        p.copy(covers = p.covers.map { it.copy(rect = it.rect.copy(x = it.rect.x + dx, y = it.rect.y + dy)) })

    fun empty(planId: Long, tMs: Long, w: Int, h: Int): Record = linkedMapOf(
        "contractVersion" to "1.0",
        "planId" to planId,
        "tMs" to tMs,
        "screenWidth" to w,
        "screenHeight" to h,
        "rotation" to 0,
        "masks" to emptyList<Any?>(),
        "reason" to "clear"
    )
}
