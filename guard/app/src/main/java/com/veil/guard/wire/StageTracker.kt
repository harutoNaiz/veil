package com.veil.guard.wire

import com.veil.brain.contract.Record

/** Emits {"kind":"stage"} lines strictly in order frame, gate, ai, judge, plan, draw per lookId. */
class StageTracker(private val emit: (Record) -> Unit) {
    private val frames = LinkedHashMap<Int, Long>()
    private val state = HashMap<Int, LongArray>() // lookId -> [lastStageIdx, lastT]
    private var lastAi: Int? = null
    private var pendingPlan: Int? = null
    private var pendingDraw: Int? = null

    @get:Synchronized
    var lastJudged: Int? = null
        private set

    @Synchronized
    fun frame(frameId: Int, t: Long) {
        frames[frameId] = t
        while (frames.size > 64) frames.remove(frames.keys.first())
    }

    @Synchronized
    fun onRecord(rec: Record) {
        when (rec["kind"]) {
            "look" -> {
                val id = (rec["lookId"] as? Number)?.toInt() ?: return
                if (rec["look"] == false) return
                val t = (rec["tMs"] as? Number)?.toLong() ?: 0L
                val ft = (rec["frameId"] as? Number)?.toInt()?.let { frames[it] } ?: t
                stage(id, 0, ft)
                stage(id, 1, t)
            }

            "plan", "maskPlan" -> {
                val id = pendingPlan ?: return
                pendingPlan = null
                val t = (rec["tMs"] as? Number)?.toLong() ?: 0L
                if (stage(id, 4, t)) pendingDraw = id
            }
        }
    }

    @Synchronized
    fun ai(lookId: Int, t: Long) {
        if (stage(lookId, 2, t)) lastAi = lookId
    }

    @Synchronized
    fun judged(t: Long) {
        val id = lastAi ?: return
        lastAi = null
        if (stage(id, 3, t)) {
            lastJudged = id
            pendingPlan = id
        }
    }

    @Synchronized
    fun onDrawn(t: Long) {
        val id = pendingDraw ?: return
        pendingDraw = null
        stage(id, 5, t)
    }

    private fun stage(id: Int, idx: Int, t: Long): Boolean {
        val s = state.getOrPut(id) { longArrayOf(-1, 0) }
        if (idx.toLong() != s[0] + 1) return false
        val tt = maxOf(t, s[1])
        s[0] = idx.toLong()
        s[1] = tt
        emit(linkedMapOf("kind" to "stage", "lookId" to id, "stage" to NAMES[idx], "tMs" to tt))
        if (state.size > 256) state.remove(state.keys.min())
        return true
    }

    private companion object {
        val NAMES = arrayOf("frame", "gate", "ai", "judge", "plan", "draw")
    }
}
