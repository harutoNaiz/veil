package com.veil.guard

import java.util.Locale

data class DeviceInfo(
    val socModel: String,
    val socManufacturer: String,
    val hardware: String,
    val board: String,
    val manufacturer: String,
    val model: String,
    val androidRelease: String,
    val sdkInt: Int,
    val buildDisplay: String,
    val ramTotalBytes: Long,
    val screenWidthPx: Int,
    val screenHeightPx: Int,
    val densityDpi: Int,
    val refreshRatesHz: List<Float>
)

object DeviceInfoFormat {
    private const val BYTES_PER_GIB = 1024.0 * 1024.0 * 1024.0

    /**
     * One-line JSON, keys in the constructor order of [DeviceInfo]; strings JSON-escaped; floats with one
     * decimal (e.g. 144.0). No org.json, so this is unit-testable on the JVM.
     */
    fun toHelloJson(info: DeviceInfo): String = buildString {
        append('{')
        appendString("socModel", info.socModel).append(',')
        appendString("socManufacturer", info.socManufacturer).append(',')
        appendString("hardware", info.hardware).append(',')
        appendString("board", info.board).append(',')
        appendString("manufacturer", info.manufacturer).append(',')
        appendString("model", info.model).append(',')
        appendString("androidRelease", info.androidRelease).append(',')
        append("\"sdkInt\":").append(info.sdkInt).append(',')
        appendString("buildDisplay", info.buildDisplay).append(',')
        append("\"ramTotalBytes\":").append(info.ramTotalBytes).append(',')
        append("\"screenWidthPx\":").append(info.screenWidthPx).append(',')
        append("\"screenHeightPx\":").append(info.screenHeightPx).append(',')
        append("\"densityDpi\":").append(info.densityDpi).append(',')
        append("\"refreshRatesHz\":[")
        append(info.refreshRatesHz.joinToString(",") { oneDecimal(it.toDouble()) })
        append("]}")
    }

    /**
     * Lines: "Veil Guard · hello", "Chip: <socModel> (<socManufacturer>)", "Android: <release> (API <sdk>)",
     * "RAM: <GiB with 1 decimal> GiB (<bytes> bytes)",
     * "Screen: <w> × <h> px, <dpi> dpi, <rates joined by '/'> Hz".
     */
    fun toDisplayText(info: DeviceInfo): String {
        val ramGib = oneDecimal(info.ramTotalBytes / BYTES_PER_GIB)
        val rates = info.refreshRatesHz.joinToString("/") { String.format(Locale.ROOT, "%.0f", it) }
        return listOf(
            "Veil Guard · hello",
            "Chip: ${info.socModel} (${info.socManufacturer})",
            "Android: ${info.androidRelease} (API ${info.sdkInt})",
            "RAM: $ramGib GiB (${info.ramTotalBytes} bytes)",
            "Screen: ${info.screenWidthPx} × ${info.screenHeightPx} px, ${info.densityDpi} dpi, $rates Hz"
        ).joinToString("\n")
    }

    private fun oneDecimal(value: Double): String = String.format(Locale.ROOT, "%.1f", value)

    private fun StringBuilder.appendString(key: String, value: String): StringBuilder {
        append('"').append(key).append("\":\"")
        for (c in value) {
            when {
                c == '"' -> append("\\\"")
                c == '\\' -> append("\\\\")
                c == '\n' -> append("\\n")
                c == '\r' -> append("\\r")
                c == '\t' -> append("\\t")
                c < ' ' -> append(String.format(Locale.ROOT, "\\u%04x", c.code))
                else -> append(c)
            }
        }
        return append('"')
    }
}
