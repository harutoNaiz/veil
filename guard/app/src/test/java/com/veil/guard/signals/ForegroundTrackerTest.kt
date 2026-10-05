package com.veil.guard.signals

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class ForegroundTrackerTest {
    @Test fun twentySwitchesWithNoise() {
        val t = ForegroundTracker("com.veil.guard")
        assertNull(t.onWindowState("com.android.systemui", null))
        val noise =
            listOf(
                "com.android.systemui",
                "com.google.android.inputmethod.latin",
                "com.veil.guard",
                "com.some.inputmethod.x",
                null
            )
        for (i in 1..20) {
            val app = "com.app.n$i"
            assertEquals(app, t.onWindowState(app, "Main"))
            for (n in noise) assertEquals(app, t.onWindowState(n, null))
        }
        assertEquals("com.app.n20", t.current)
    }
}
