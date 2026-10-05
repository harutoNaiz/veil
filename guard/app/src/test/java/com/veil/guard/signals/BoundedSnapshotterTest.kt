package com.veil.guard.signals

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

private class FakeNode(
    override val className: String?,
    override val text: String? = null,
    override val visible: Boolean = true,
    val kids: List<FakeNode> = emptyList()
) : SnapSourceNode {
    override val rect = PxRect(0, 0, 10, 10)
    override val contentDescription: String? = null
    override val viewId: String? = null
    override val childCount get() = kids.size

    override fun child(i: Int): SnapSourceNode? = kids[i]
}

class BoundedSnapshotterTest {
    private fun wide(n: Int) = FakeNode("Root", kids = List(n) { FakeNode("android.widget.TextView", "t$it") })

    @Test
    fun capsAt300() {
        val s = BoundedSnapshotter({ wide(1000) }, { 0L })
        val r = s.snapshot()!!
        assertTrue(r.truncated)
        assertTrue(r.nodes.size <= 300)
    }

    @Test
    fun stopsAtBudget() {
        var t = 0L
        val s = BoundedSnapshotter({ wide(1000) }, { t++ }, maxNodes = 10_000)
        val r = s.snapshot()!!
        assertTrue(r.truncated)
        assertTrue(r.durationMs in 40L..45L)
    }

    @Test
    fun minGap() {
        var t = 1000L
        val s = BoundedSnapshotter({ wide(2) }, { t })
        assertNotNull(s.snapshot())
        t += 100
        assertNull(s.snapshot())
        t += 150
        assertNotNull(s.snapshot())
    }

    @Test
    fun kindsAndInvisible() {
        val root =
            FakeNode(
                "Root",
                kids =
                    listOf(
                        FakeNode("android.widget.ImageView"),
                        FakeNode("androidx.media3.ui.PlayerView"),
                        FakeNode("android.webkit.WebView"),
                        FakeNode("android.view.View", "hello"),
                        FakeNode("androidx.recyclerview.widget.RecyclerView"),
                        FakeNode("android.view.View"),
                        FakeNode("android.widget.ImageView", visible = false),
                        FakeNode("android.view.View", "x".repeat(3000))
                    )
            )
        val r = BoundedSnapshotter({ root }, { 0L }).snapshot()!!
        assertEquals(listOf("image", "video", "web", "text", "list", "text"), r.nodes.map { it.kind })
        assertEquals(2000, r.nodes.last().text!!.length)
        assertFalse(r.truncated)
    }
}
