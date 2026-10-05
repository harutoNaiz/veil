package com.veil.guard.signals

/** Hand-written JSON for [UiEvent] (org.json is a stub in JVM tests). Nulls are omitted. */
object UiEventJson {
    fun toJson(e: UiEvent): String {
        val sb = StringBuilder("{\"contractVersion\":\"1.0\",\"eventId\":").append(e.eventId)
        sb.append(",\"tMs\":").append(maxOf(0L, e.tMs))
        sb.append(",\"type\":\"").append(typeOf(e)).append('"')
        e.packageName?.let {
            sb.append(",\"packageName\":")
            str(sb, it)
        }
        when (e) {
            is Scrolled -> scrolled(sb, e)

            is WindowChanged -> {
                e.className?.let {
                    sb.append(",\"className\":")
                    str(sb, it.take(200))
                }
                e.windowId?.let { sb.append(",\"windowId\":").append(it) }
            }

            is ContentChanged -> {
                e.rect?.let { rect(sb, "rect", it) }
                if (e.changeTypes.isNotEmpty()) {
                    sb.append(",\"changeTypes\":[")
                    e.changeTypes.take(8).forEachIndexed { i, s ->
                        if (i > 0) sb.append(',')
                        str(sb, s.take(32))
                    }
                    sb.append(']')
                }
            }

            is NodesSnapshot -> {
                sb.append(",\"nodes\":[")
                e.nodes.take(300).forEachIndexed { i, n ->
                    if (i > 0) sb.append(',')
                    node(sb, n)
                }
                sb.append("],\"truncated\":").append(e.truncated)
                sb.append(",\"durationMs\":").append(maxOf(0L, e.durationMs))
            }

            is ScreenOff, is ScreenOn -> Unit
        }
        return sb.append('}').toString()
    }

    private fun scrolled(sb: StringBuilder, e: Scrolled) {
        sb.append(",\"dx\":").append(e.dx).append(",\"dy\":").append(e.dy)
        e.containerRect?.let { rect(sb, "containerRect", it) }
        e.containerId?.let {
            sb.append(",\"containerId\":")
            str(sb, it.take(128))
        }
        if (e.estimated) sb.append(",\"estimated\":true")
    }

    private fun typeOf(e: UiEvent) = when (e) {
        is Scrolled -> "scrolled"
        is WindowChanged -> "windowChanged"
        is ContentChanged -> "contentChanged"
        is NodesSnapshot -> "nodesSnapshot"
        is ScreenOff -> "screenOff"
        is ScreenOn -> "screenOn"
    }

    private fun node(sb: StringBuilder, n: SnapNode) {
        sb.append("{\"kind\":\"").append(n.kind).append('"')
        val r = n.rect
        sb.append(",\"rect\":{\"x\":").append(r.x).append(",\"y\":").append(r.y)
        sb.append(",\"w\":").append(maxOf(1, r.w)).append(",\"h\":").append(maxOf(1, r.h)).append('}')
        n.nodeId?.let {
            sb.append(",\"nodeId\":")
            str(sb, it.take(128))
        }
        n.text?.let {
            sb.append(",\"text\":")
            str(sb, it.take(2000))
        }
        n.contentDescription?.let {
            sb.append(",\"contentDescription\":")
            str(sb, it.take(500))
        }
        n.className?.let {
            sb.append(",\"className\":")
            str(sb, it.take(200))
        }
        sb.append('}')
    }

    private fun rect(sb: StringBuilder, key: String, r: PxRect) {
        if (r.w < 1 || r.h < 1) return
        sb.append(",\"").append(key).append("\":{\"x\":").append(r.x).append(",\"y\":").append(r.y)
        sb.append(",\"w\":").append(r.w).append(",\"h\":").append(r.h).append('}')
    }

    private fun str(sb: StringBuilder, s: String) {
        sb.append('"')
        for (c in s) {
            when {
                c == '"' -> sb.append("\\\"")
                c == '\\' -> sb.append("\\\\")
                c == '\n' -> sb.append("\\n")
                c == '\r' -> sb.append("\\r")
                c == '\t' -> sb.append("\\t")
                c < ' ' -> sb.append(String.format("\\u%04x", c.code))
                else -> sb.append(c)
            }
        }
        sb.append('"')
    }
}
