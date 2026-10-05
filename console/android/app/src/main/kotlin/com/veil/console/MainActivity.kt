package com.veil.console

import com.veil.console.bridge.GuardHostApi
import com.veil.console.bridge.GuardHostImpl
import com.veil.console.bridge.NoGuardBackend
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine

class MainActivity : FlutterActivity() {
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        GuardHostApi.setUp(flutterEngine.dartExecutor.binaryMessenger, GuardHostImpl(NoGuardBackend(this)))
    }
}
