package com.veil.guard.wire

import com.veil.brain.contract.Record
import org.junit.Assert.assertEquals
import org.junit.Test

class StageTrackerTest {
    private val out = ArrayList<Record>()
    private val st = StageTracker { out.add(it) }

    private fun look(id: Int, t: Long): Record = mapOf("kind" to "look", "lookId" to id, "frameId" to 1, "tMs" to t)

    private fun stages(id: Int) = out.filter { it["lookId"] == id }.map { it["stage"] }

    @Test fun outOfOrderNeverEmitsLaterBeforeEarlier() {
        st.ai(1, 5)
        st.judged(6)
        st.onRecord(mapOf("kind" to "plan", "tMs" to 7L))
        st.onDrawn(8)
        assertEquals(0, out.size)
        st.frame(1, 3)
        st.onRecord(look(1, 4))
        st.onDrawn(9)
        st.onRecord(mapOf("kind" to "plan", "tMs" to 10L))
        st.judged(11)
        assertEquals(listOf("frame", "gate"), stages(1))
        st.ai(1, 12)
        st.judged(13)
        st.onRecord(mapOf("kind" to "plan", "tMs" to 14L))
        st.onDrawn(15)
        assertEquals(listOf("frame", "gate", "ai", "judge", "plan", "draw"), stages(1))
        val ts = out.map { (it["tMs"] as Number).toLong() }
        assertEquals(ts.sorted(), ts)
    }
}
