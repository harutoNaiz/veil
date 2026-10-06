package com.veil.guard.overlay.blind

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class BlindHintPolicyTest {
    @Test fun debounce() {
        val p = BlindHintPolicy()
        assertFalse(p.onFrame("nf", true, 0))
        assertFalse(p.onFrame("nf", true, 1999))
        assertTrue(p.onFrame("nf", true, 2000))
    }

    @Test fun appSwitchHides() {
        val p = BlindHintPolicy()
        p.onFrame("nf", true, 0)
        assertTrue(p.onFrame("nf", true, 2500))
        assertFalse(p.onFrame("other", true, 2600))
        assertFalse(p.onFrame("other", true, 3000))
        assertTrue(p.onFrame("other", true, 4600))
    }

    @Test fun recoveryHidesAndResetsTimer() {
        val p = BlindHintPolicy()
        p.onFrame("nf", true, 0)
        assertTrue(p.onFrame("nf", true, 2000))
        assertFalse(p.onFrame("nf", false, 2100))
        assertFalse(p.onFrame("nf", true, 2200))
        assertTrue(p.onFrame("nf", true, 4200))
    }

    @Test fun dismissPerApp() {
        val p = BlindHintPolicy()
        p.onFrame("nf", true, 0)
        p.onFrame("nf", true, 2000)
        p.dismiss()
        assertFalse(p.visible)
        assertFalse(p.onFrame("nf", true, 9000))
        p.onFrame("b", true, 9100)
        assertTrue(p.onFrame("b", true, 11100))
    }
}
