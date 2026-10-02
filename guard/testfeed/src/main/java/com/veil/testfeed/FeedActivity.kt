package com.veil.testfeed

import android.app.Activity
import android.graphics.Color
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.util.Log
import android.util.TypedValue
import android.view.Choreographer
import android.view.Gravity
import android.view.MotionEvent
import android.view.View
import android.view.ViewConfiguration
import android.view.ViewGroup
import android.view.ViewTreeObserver
import android.view.WindowInsets
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import java.io.File
import kotlin.math.abs

/**
 * The Test Feed: a scrolling list of 60 placeholder items. It writes what is on screen, frame by frame, to
 * filesDir/feedlog.jsonl (format in guard/testfeed/README.md), so a test can compare it with what the Guard sees.
 */
class FeedActivity : Activity() {
    private lateinit var logger: FeedLogger
    private lateinit var scrollView: ScrollView
    private lateinit var content: LinearLayout
    private val handler = Handler(Looper.getMainLooper())

    private var layouts: List<ItemLayout> = emptyList()
    private var viewport = IntRect(0, 0, 0, 0)
    private var sessionLogged = false
    private var lastLoggedScrollY = Int.MIN_VALUE
    private var touchSlop = 0
    private var downX = 0f
    private var downY = 0f
    private var downTimeMs = 0L

    private val frameCallback =
        object : Choreographer.FrameCallback {
            override fun doFrame(frameTimeNanos: Long) {
                logFrameIfScrolled(frameTimeNanos / NANOS_PER_MS)
                Choreographer.getInstance().postFrameCallback(this)
            }
        }

    private val flushRunnable =
        object : Runnable {
            override fun run() {
                logger.flush()
                handler.postDelayed(this, FLUSH_INTERVAL_MS)
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        logger = FeedLogger(File(filesDir, LOG_NAME))
        touchSlop = ViewConfiguration.get(this).scaledTouchSlop

        val density = resources.displayMetrics.density
        val items = FeedItems.defaultFeed()
        content = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        items.forEach { content.addView(buildItemView(it, density)) }
        scrollView = ScrollView(this).apply { addView(content) }

        val root =
            FrameLayout(this).apply {
                setBackgroundColor(Color.WHITE)
                addView(scrollView, FrameLayout.LayoutParams(MATCH, MATCH))
                // targetSdk 35+ draws edge to edge: keep the feed clear of the system bars.
                setOnApplyWindowInsetsListener { view, insets ->
                    val bars = insets.getInsets(WindowInsets.Type.systemBars())
                    view.setPadding(bars.left, bars.top, bars.right, bars.bottom)
                    insets
                }
            }
        setContentView(root)

        scrollView.viewTreeObserver.addOnGlobalLayoutListener(
            object : ViewTreeObserver.OnGlobalLayoutListener {
                override fun onGlobalLayout() {
                    if (content.height == 0) return
                    scrollView.viewTreeObserver.removeOnGlobalLayoutListener(this)
                    logSession(items)
                }
            }
        )
        Log.i(TAG, "VEIL_FEED session items=${items.size}")
    }

    override fun onResume() {
        super.onResume()
        Choreographer.getInstance().postFrameCallback(frameCallback)
        handler.postDelayed(flushRunnable, FLUSH_INTERVAL_MS)
    }

    override fun onPause() {
        Choreographer.getInstance().removeFrameCallback(frameCallback)
        handler.removeCallbacks(flushRunnable)
        logger.log(FeedJson.pause(SystemClock.uptimeMillis()))
        logger.flush()
        super.onPause()
    }

    override fun onDestroy() {
        logger.close()
        super.onDestroy()
    }

    override fun dispatchTouchEvent(event: MotionEvent): Boolean {
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN -> {
                downX = event.rawX
                downY = event.rawY
                downTimeMs = event.eventTime
            }

            MotionEvent.ACTION_UP -> {
                val withinSlop = abs(event.rawX - downX) <= touchSlop && abs(event.rawY - downY) <= touchSlop
                if (sessionLogged && withinSlop && event.eventTime - downTimeMs < TAP_MAX_MS) {
                    val x = event.rawX.toInt()
                    val y = event.rawY.toInt()
                    val itemId = FeedGeometry.hitTest(layouts, scrollView.scrollY, viewport, x, y)
                    logger.log(FeedJson.tap(event.eventTime, x, y, itemId))
                }
            }
        }
        return super.dispatchTouchEvent(event)
    }

    private fun buildItemView(item: FeedItem, density: Float): View {
        val heightPx = (item.heightDp * density).toInt()
        val params =
            LinearLayout.LayoutParams(MATCH, heightPx).apply { bottomMargin = (BOTTOM_MARGIN_DP * density).toInt() }
        val view: View =
            if (item.kind == "ruler") {
                RulerView(this)
            } else {
                FrameLayout(this).apply {
                    setBackgroundColor(item.color)
                    addView(
                        TextView(context).apply {
                            text = item.label
                            setTextSize(TypedValue.COMPLEX_UNIT_SP, LABEL_SIZE_SP)
                            setTextColor(Color.BLACK)
                            gravity = Gravity.CENTER
                        },
                        FrameLayout.LayoutParams(MATCH, MATCH)
                    )
                }
            }
        view.layoutParams = params
        view.tag = item.id
        return view
    }

    private fun logSession(items: List<FeedItem>) {
        layouts =
            items.mapIndexed { index, item ->
                val child = content.getChildAt(index)
                ItemLayout(item.id, item.kind, child.top, child.height)
            }
        val location = IntArray(2)
        scrollView.getLocationOnScreen(location)
        viewport = IntRect(location[0], location[1], scrollView.width, scrollView.height)
        val screen = windowManager.currentWindowMetrics.bounds
        logger.log(
            FeedJson.session(
                SystemClock.uptimeMillis(),
                screen.width(),
                screen.height(),
                resources.displayMetrics.densityDpi,
                viewport,
                layouts
            )
        )
        sessionLogged = true
    }

    private fun logFrameIfScrolled(tMs: Long) {
        if (!sessionLogged) return
        val scrollY = scrollView.scrollY
        if (scrollY == lastLoggedScrollY) return
        lastLoggedScrollY = scrollY
        logger.log(FeedJson.frame(tMs, scrollY, FeedGeometry.visible(layouts, scrollY, viewport)))
    }

    private companion object {
        const val TAG = "VeilFeed"
        const val LOG_NAME = "feedlog.jsonl"
        const val MATCH = ViewGroup.LayoutParams.MATCH_PARENT
        const val BOTTOM_MARGIN_DP = 8
        const val LABEL_SIZE_SP = 28f
        const val FLUSH_INTERVAL_MS = 500L
        const val TAP_MAX_MS = 500L
        const val NANOS_PER_MS = 1_000_000L
    }
}
