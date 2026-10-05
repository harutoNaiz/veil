package com.veil.guard.overlay

object PlanDiff {
    fun diff(old: CoverPlan?, new: CoverPlan): PlanDelta {
        val before = old?.covers?.associateBy { it.maskId } ?: emptyMap()
        val after = new.covers.associateBy { it.maskId }
        val added = new.covers.filter { it.maskId !in before }
        val removed = before.keys.filter { it !in after }
        val changed = new.covers.filter { c -> before[c.maskId]?.let { it != c } == true }
        return PlanDelta(added, removed, changed)
    }
}
