package com.veil.conductor

import com.veil.brain.contract.Finding
import com.veil.brain.contract.Record

/** Jobs wait until the test completes them; busy while any job is pending unless alwaysFree. */
class ManualWorker(private val alwaysFree: Boolean = false) : AiWorker {
    class Pending(
        val tag: Int,
        val startMs: Long,
        val job: () -> List<Finding>,
        val done: (List<Finding>, Long) -> Unit
    )

    val pending = ArrayList<Pending>()
    var maxPending = 0
    var tag = 0
    var now = 0L
    override val busy get() = !alwaysFree && pending.isNotEmpty()

    override fun submit(job: () -> List<Finding>, done: (List<Finding>, Long) -> Unit) {
        pending.add(Pending(tag, now, job, done))
        maxPending = maxOf(maxPending, pending.size)
    }

    fun complete(p: Pending, aiMs: Long = 1) {
        pending.remove(p)
        p.done(p.job(), aiMs)
    }

    fun completeDue(t: Long, takesMs: Long) {
        pending.filter { t - it.startMs >= takesMs }.forEach { complete(it, takesMs) }
    }
}

class ScriptedLane(private val byFrame: Map<Int, List<Finding>> = emptyMap()) : Lane {
    override fun run(input: LookInput): List<Finding> = byFrame[input.frame.meta.frameId] ?: emptyList()
}

class RecordingOverlay : OverlayPort {
    val plans = ArrayList<Record>()
    val calls = ArrayList<String>()

    override fun submit(plan: Record) {
        plans.add(plan)
        calls.add("plan")
    }

    override fun shift(dx: Int, dy: Int, tMs: Long) {
        calls.add("shift")
    }
}
