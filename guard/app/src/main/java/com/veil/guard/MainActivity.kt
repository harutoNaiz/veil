package com.veil.guard

import android.app.Activity
import android.os.Bundle
import android.util.Log
import android.view.WindowInsets
import android.widget.ScrollView
import android.widget.TextView
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.MainScope
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/** Hello world for the Guard: shows what this phone is and logs the same facts as one JSON line. */
class MainActivity : Activity() {
    private val scope = MainScope()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val textView =
            TextView(this).apply {
                textSize = 18f
                setPadding(PADDING_PX, PADDING_PX, PADDING_PX, PADDING_PX)
                text = "Veil Guard · starting"
            }
        val scrollView =
            ScrollView(this).apply {
                addView(textView)
                // targetSdk 35+ draws edge to edge: keep the text clear of the system bars.
                setOnApplyWindowInsetsListener { view, insets ->
                    val bars = insets.getInsets(WindowInsets.Type.systemBars())
                    view.setPadding(bars.left, bars.top, bars.right, bars.bottom)
                    insets
                }
            }
        setContentView(scrollView)

        scope.launch {
            val info = readDeviceInfo(this@MainActivity)
            val text =
                withContext(Dispatchers.Default) {
                    DeviceInfoFormat.toDisplayText(info) to DeviceInfoFormat.toHelloJson(info)
                }
            textView.text = text.first
            Log.i(TAG, "VEIL_HELLO " + text.second)
        }
    }

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }

    companion object {
        const val TAG = "VeilHello"
        private const val PADDING_PX = 48
    }
}
