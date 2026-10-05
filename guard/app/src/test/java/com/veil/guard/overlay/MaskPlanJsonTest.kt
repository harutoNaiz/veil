package com.veil.guard.overlay

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class MaskPlanJsonTest {
    private fun example(): String {
        var d: File? = File("").absoluteFile
        while (d != null && !File(d, "contracts/examples/mask-plan").isDirectory) d = d.parentFile
        val dir = File(d, "contracts/examples/mask-plan")
        return File(dir, "valid-01-two-covers.json").readText()
    }

    @Test
    fun parsesExample() {
        val p = MaskPlanJson.parse(example())
        assertEquals(57L, p.planId)
        assertEquals(1440, p.screenW)
        assertTrue(p.covers.isNotEmpty())
        assertEquals(CoverStyle.BLUR, p.covers[0].style)
        assertTrue(p.covers[0].peekable)
        assertEquals(Px(48, 88, 1344, 1344), p.covers[0].rect)
    }

    @Test
    fun rejectsOtherVersion() {
        val bad = example().replaceFirst("\"contractVersion\": \"1.0\"", "\"contractVersion\": \"2.0\"")
        val r = runCatching { MaskPlanJson.parse(bad) }
        assertTrue(r.isFailure)
    }
}
