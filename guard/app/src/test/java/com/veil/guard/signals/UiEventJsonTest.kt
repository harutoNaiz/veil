package com.veil.guard.signals

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class UiEventJsonTest {
    @Test fun scrolledKeysAndOmittedNulls() {
        val j = UiEventJson.toJson(Scrolled(3, 99, "com.a.b", 0, -40))
        assertEquals(
            "{\"contractVersion\":\"1.0\",\"eventId\":3,\"tMs\":99,\"type\":\"scrolled\",\"packageName\":\"com.a.b\",\"dx\":0,\"dy\":-40}",
            j
        )
        assertFalse(j.contains("containerRect"))
        assertFalse(j.contains("estimated"))
    }

    @Test fun escaping() {
        val j = UiEventJson.toJson(WindowChanged(1, 1, "com.a.b", "a\"b\\c\n"))
        assertTrue(j.contains("\"className\":\"a\\\"b\\\\c\\n\""))
    }

    @Test fun writes1000() {
        val pkg = "com.example.app"
        val node = SnapNode("text", PxRect(0, 0, 10, 10), "n1", "hi \"there\"", "d", "android.widget.TextView")
        val lines =
            (0 until 1000).map { i ->
                val id = i.toLong()
                val t = 1000L + i
                when (i % 6) {
                    0 -> Scrolled(id, t, pkg, 0, -i, PxRect(0, 0, 1080, 2000), "com.example.app:id/list", i % 12 == 0)
                    1 -> WindowChanged(id, t, pkg, "com.example.Main", i)
                    2 -> ContentChanged(id, t, null, PxRect(1, 2, 3, 4), listOf("text", "subtree"))
                    3 -> NodesSnapshot(id, t, pkg, listOf(node), i % 12 == 3, 12)
                    4 -> ScreenOff(id, t)
                    else -> ScreenOn(id, t, pkg)
                }
            }.map(UiEventJson::toJson)
        val f = File("build/tmp/uievents-1000.jsonl")
        f.parentFile.mkdirs()
        f.writeText(lines.joinToString("\n", postfix = "\n"))
        assertEquals(1000, f.readLines().size)
    }
}
