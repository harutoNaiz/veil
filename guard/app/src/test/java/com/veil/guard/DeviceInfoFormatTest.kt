package com.veil.guard

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class DeviceInfoFormatTest {
    private val sample =
        DeviceInfo(
            socModel = "SM8850",
            socManufacturer = "QTI",
            hardware = "qcom",
            board = "canoe",
            manufacturer = "vivo",
            model = "iQOO 15",
            androidRelease = "16",
            sdkInt = 36,
            buildDisplay = "OriginOS.16.0",
            ramTotalBytes = 17_179_869_184L,
            screenWidthPx = 1440,
            screenHeightPx = 3168,
            densityDpi = 560,
            refreshRatesHz = listOf(60f, 120f, 144f)
        )

    @Test
    fun helloJsonIsExact() {
        val expected =
            "{\"socModel\":\"SM8850\",\"socManufacturer\":\"QTI\",\"hardware\":\"qcom\",\"board\":\"canoe\"," +
                "\"manufacturer\":\"vivo\",\"model\":\"iQOO 15\",\"androidRelease\":\"16\",\"sdkInt\":36," +
                "\"buildDisplay\":\"OriginOS.16.0\",\"ramTotalBytes\":17179869184,\"screenWidthPx\":1440," +
                "\"screenHeightPx\":3168,\"densityDpi\":560,\"refreshRatesHz\":[60.0,120.0,144.0]}"
        assertEquals(expected, DeviceInfoFormat.toHelloJson(sample))
    }

    @Test
    fun helloJsonEscapesStrings() {
        val json = DeviceInfoFormat.toHelloJson(sample.copy(model = "a\"b\\c\nd"))
        assertTrue(json, json.contains("\"model\":\"a\\\"b\\\\c\\nd\""))
    }

    @Test
    fun displayTextShowsChipAndAndroid() {
        val text = DeviceInfoFormat.toDisplayText(sample)
        assertTrue(text, text.contains("Chip: SM8850 (QTI)"))
        assertTrue(text, text.contains("Android: 16 (API 36)"))
        assertTrue(text, text.contains("RAM: 16.0 GiB (17179869184 bytes)"))
        assertTrue(text, text.contains("Screen: 1440 × 3168 px, 560 dpi, 60/120/144 Hz"))
    }
}
