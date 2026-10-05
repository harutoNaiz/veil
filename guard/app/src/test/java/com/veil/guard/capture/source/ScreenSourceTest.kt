package com.veil.guard.capture.source

import com.veil.guard.capture.CaptureGeometry
import com.veil.guard.capture.FrameSize
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class ScreenSourceTest {
    private class FakePort : DisplayPort {
        var creates = 0
        var attaches = 0
        var detaches = 0
        val resizes = mutableListOf<FrameSize>()

        override fun create(size: FrameSize, dpi: Int) {
            creates++
        }

        override fun setSurfaceAttached(on: Boolean) {
            if (on) attaches++ else detaches++
        }

        override fun resize(size: FrameSize, dpi: Int) {
            resizes += size
        }
    }

    @Test
    fun geometry1080() = assertEquals(FrameSize(360, 800), CaptureGeometry.targetSize(FrameSize(1080, 2400)))

    @Test
    fun geometry1440() = assertEquals(FrameSize(360, 792), CaptureGeometry.targetSize(FrameSize(1440, 3168)))

    @Test
    fun geometryLandscape() = assertEquals(FrameSize(792, 360), CaptureGeometry.targetSize(FrameSize(3168, 1440)))

    @Test
    fun pauseResumeNeverRecreates() {
        val p = FakePort()
        val c = ScreenSourceCore(p, FrameSize(1080, 2400), 420)
        c.start()
        repeat(10) {
            c.pause()
            c.resume()
        }
        assertEquals(1, p.creates)
        assertEquals(10, p.detaches)
        assertEquals(11, p.attaches)
        assertThrows(IllegalStateException::class.java) { c.start() }
    }

    @Test
    fun rotationResizesNotCreates() {
        val p = FakePort()
        val c = ScreenSourceCore(p, FrameSize(1080, 2400), 420)
        c.start()
        c.rotate(FrameSize(2400, 1080))
        assertEquals(1, p.creates)
        assertEquals(listOf(FrameSize(800, 360)), p.resizes)
    }

    @Test
    fun gateAtMostOneOutstanding() {
        val g = FrameGate()
        assertTrue(g.tryAcquire())
        assertFalse(g.tryAcquire())
        assertFalse(g.tryAcquire())
        assertEquals(1, g.outstanding)
        assertEquals(2L, g.dropped)
        g.release()
        assertEquals(0, g.outstanding)
        assertTrue(g.tryAcquire())
    }

    @Test
    fun meterFps() {
        val m = FrameRateMeter()
        for (i in 0 until 30) m.record(i * 100L)
        assertEquals(10.0, m.fps1s(2_900), 0.01)
        assertEquals(3.0, m.fps10s(2_900), 0.01)
    }

    @Test
    fun meterIdleIsZero() {
        val m = FrameRateMeter()
        m.record(0)
        assertEquals(0.0, m.fps1s(5_000), 0.0)
    }
}
