package com.veil.guard.wire

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class MlKitOcrBoxTest {
    @Test fun bigBoxUnchanged() {
        assertArrayEquals(intArrayOf(10, 20, 100, 80), ocrBox(10, 20, 100, 80, 360, 780))
    }

    @Test fun tinyBoxGrowsToMinimumInsideFrame() {
        for ((x, y) in listOf(100 to 100, 0 to 0, 359 to 779, 350 to 5)) {
            val b = ocrBox(x, y, 4, 1, 360, 780)!!
            assertTrue(b[2] >= 32 && b[3] >= 32)
            assertTrue(b[0] >= 0 && b[1] >= 0 && b[0] + b[2] <= 360 && b[1] + b[3] <= 780)
        }
    }

    @Test fun frameTooSmallIsSkipped() {
        assertNull(ocrBox(0, 0, 10, 10, 20, 780))
    }
}
