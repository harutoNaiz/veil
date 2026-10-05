package com.veil.guard.overlay

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class CoverGeometryTest {
    private val plan = CoverPlan(1, 0, 1000, 2000, 0, emptyList(), "t")

    @Test
    fun identity() {
        assertEquals(Px(10, 20, 30, 40), CoverGeometry.toDisplay(Px(10, 20, 30, 40), plan, DisplayState(1000, 2000, 0)))
    }

    @Test
    fun scales() {
        assertEquals(Px(5, 10, 15, 20), CoverGeometry.toDisplay(Px(10, 20, 30, 40), plan, DisplayState(500, 1000, 0)))
    }

    @Test
    fun rotate90() {
        // (x=100,y=200,w=300,h=400) in 1000x2000 -> x'=y, y'=1000-(x+w) in 2000x1000
        assertEquals(
            Px(200, 600, 400, 300),
            CoverGeometry.toDisplay(Px(100, 200, 300, 400), plan, DisplayState(2000, 1000, 1))
        )
    }

    @Test
    fun rotate270Back() {
        val land = plan.copy(screenW = 2000, screenH = 1000, rotation = 1)
        assertEquals(
            Px(100, 200, 300, 400),
            CoverGeometry.toDisplay(Px(200, 600, 400, 300), land, DisplayState(1000, 2000, 0))
        )
    }

    @Test
    fun clampAndPad() {
        assertEquals(Px(0, 0, 55, 55), CoverGeometry.toDisplay(Px(0, 0, 50, 50), plan, DisplayState(1000, 2000, 0), 5))
        assertEquals(
            Px(950, 1950, 50, 50),
            CoverGeometry.toDisplay(Px(950, 1950, 100, 100), plan, DisplayState(1000, 2000, 0))
        )
        assertNull(CoverGeometry.toDisplay(Px(1200, 0, 50, 50), plan, DisplayState(1000, 2000, 0)))
    }
}
