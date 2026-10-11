package com.veil.guard

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.content.res.Configuration
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.os.Bundle
import android.provider.Settings
import android.text.InputType
import android.util.Log
import android.util.TypedValue
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.view.WindowInsets
import android.view.inputmethod.EditorInfo
import android.view.inputmethod.InputMethodManager
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.RadioButton
import android.widget.RadioGroup
import android.widget.ScrollView
import android.widget.Switch
import android.widget.TextView
import com.veil.guard.app.Parental
import com.veil.guard.app.VeilSettings
import com.veil.guard.app.WordLibrary
import com.veil.guard.capture.service.CaptureCommandReceiver
import com.veil.guard.capture.service.CaptureService
import com.veil.guard.wire.GuardRuntime
import kotlin.concurrent.thread
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.MainScope
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * Veil's home screen: setup, the protection switch, the built-in categories, the user's own words (type a word,
 * it is learned on the phone and hidden from then on) and the sensitivity. Everything runs on this phone.
 */
class MainActivity : Activity() {
    private val scope = MainScope()
    private val night get() =
        resources.configuration.uiMode and Configuration.UI_MODE_NIGHT_MASK == Configuration.UI_MODE_NIGHT_YES
    private val bg get() = if (night) 0xFF121417.toInt() else 0xFFF4F5F8.toInt()
    private val card get() = if (night) 0xFF1E2126.toInt() else Color.WHITE
    private val ink get() = if (night) 0xFFECEFF3.toInt() else 0xFF1B1E23.toInt()
    private val sub get() = if (night) 0xFF9AA1AB.toInt() else 0xFF5F6670.toInt()
    private val accent = 0xFF3B6FE0.toInt()

    private lateinit var setupCard: View
    private lateinit var content: View
    private lateinit var parentNote: TextView
    private lateinit var activityToday: TextView
    private lateinit var activityBreak: TextView
    private lateinit var activityApps: TextView
    private lateinit var activityBars: WeekBars
    private lateinit var childSwitch: Switch
    private lateinit var childRow: View
    private lateinit var parentSetup: Button
    private lateinit var lockNow: Button
    private lateinit var alwaysNote: TextView
    private var asking = false
    private lateinit var protection: Switch
    private lateinit var protectionNote: TextView
    private lateinit var nudity: Switch
    private val packSwitches = HashMap<String, Switch>()
    private lateinit var wordInput: EditText
    private lateinit var addButton: Button
    private lateinit var wordStatus: TextView
    private lateinit var wordList: LinearLayout
    private lateinit var modes: RadioGroup
    private lateinit var coverModes: RadioGroup

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // The recent-apps preview must not show the parent's settings either.
        if (android.os.Build.VERSION.SDK_INT >= 33) setRecentsScreenshotEnabled(false)
        setContentView(build())
        firstRun()
        scope.launch {
            val info = readDeviceInfo(this@MainActivity)
            val json = withContext(Dispatchers.Default) { DeviceInfoFormat.toHelloJson(info) }
            Log.i(TAG, "VEIL_HELLO $json")
        }
    }

    override fun onResume() {
        super.onResume()
        if (isFinishing) return
        if (Parental.hasPin(this) && !Parental.isUnlocked(this)) {
            content.visibility = View.INVISIBLE
            if (!asking) {
                asking = true
                startActivityForResult(Intent(this, ParentLockActivity::class.java), REQ_UNLOCK)
            }
            return
        }
        content.visibility = View.VISIBLE
        // After an update, crash or reboot the switch may say On while the guard is not running: resume it.
        if (VeilSettings.protectionOn(this) && accessibilityOn()) command("source", "a11y")
        refresh()
    }

    /**
     * Leaving Veil (home, another app, recents) locks it at once, so a child picking the phone up next always meets
     * the PIN screen. Safe for our own PIN screen: a correct PIN unlocks again right after this.
     */
    override fun onStop() {
        super.onStop()
        if (Parental.hasPin(this) && !isChangingConfigurations) {
            Parental.lock()
            content.visibility = View.INVISIBLE
        }
    }

    @Deprecated("Deprecated in Java")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        asking = false
        when {
            resultCode != RESULT_OK -> if (requestCode == REQ_UNLOCK) finish()
            requestCode == REQ_SETUP -> applyMode(true)
        }
    }

    /** Switches child/adult mode: swaps the word list and packs, then makes the running guard rebuild. */
    private fun applyMode(child: Boolean) {
        Parental.setChildMode(this, child)
        thread {
            runCatching { WordLibrary.syncProfile(this) }
            runOnUiThread {
                GuardRuntime.reloadLanes()
                if (VeilSettings.protectionOn(this) && accessibilityOn()) command("source", "a11y")
                refresh()
            }
        }
    }

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }

    // ---- layout ----

    private fun dp(v: Int) =
        TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, v.toFloat(), resources.displayMetrics).toInt()

    private fun text(s: String, size: Float, color: Int, bold: Boolean = false) = TextView(this).apply {
        text = s
        textSize = size
        setTextColor(color)
        if (bold) typeface = Typeface.DEFAULT_BOLD
    }

    private fun cardBox(vararg children: View) = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(dp(18), dp(16), dp(18), dp(16))
        background = GradientDrawable().apply {
            setColor(card)
            cornerRadius = dp(18).toFloat()
        }
        children.forEach { addView(it) }
        layoutParams =
            LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
                .apply { topMargin = dp(14) }
    }

    private fun button(label: String, primary: Boolean, onClick: () -> Unit) = Button(this).apply {
        text = label
        isAllCaps = false
        setTextColor(if (primary) Color.WHITE else accent)
        background = GradientDrawable().apply {
            setColor(if (primary) accent else Color.TRANSPARENT)
            setStroke(dp(1), accent)
            cornerRadius = dp(12).toFloat()
        }
        setOnClickListener { onClick() }
    }

    private fun switchRow(title: String, note: String?, sw: Switch) = LinearLayout(this).apply {
        orientation = LinearLayout.HORIZONTAL
        gravity = Gravity.CENTER_VERTICAL
        setPadding(0, dp(8), 0, dp(8))
        addView(
            LinearLayout(context).apply {
                orientation = LinearLayout.VERTICAL
                addView(text(title, 16f, ink, bold = true))
                note?.let { addView(text(it, 13f, sub)) }
            },
            LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
        )
        addView(sw)
    }

    private fun build(): View {
        val col = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(12), dp(18), dp(28))
        }
        col.addView(text("Veil", 30f, ink, bold = true))
        col.addView(text("Hides what you don't want to see. Everything runs on this phone.", 14f, sub))

        setupCard = cardBox(
            text("Finish setup", 17f, ink, bold = true),
            text(
                "Veil needs its Accessibility service to see the screen and draw blurs. " +
                    "Open Accessibility, choose Veil Guard and turn it on. If Android says the setting is " +
                    "restricted, open App info, tap ⋮ and choose \"Allow restricted settings\" first.",
                14f,
                sub
            ),
            LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL
                setPadding(0, dp(10), 0, 0)
                addView(
                    button("Open Accessibility", true) { startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)) }
                )
                addView(View(context), LinearLayout.LayoutParams(dp(10), 1))
                addView(
                    button("App info", false) {
                        startActivity(
                            Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:$packageName"))
                        )
                    }
                )
            }
        )
        col.addView(setupCard)

        parentNote = text("", 14f, sub)
        childSwitch = Switch(this)
        childSwitch.setOnCheckedChangeListener { sw, on ->
            if (!sw.isPressed) return@setOnCheckedChangeListener
            if (Parental.isUnlocked(this)) applyMode(on) else refresh()
        }
        childRow = switchRow("Child mode (parental control)", null, childSwitch)
        parentSetup = button("Set up parental control", true) {
            asking = true
            startActivityForResult(Intent(this, ParentLockActivity::class.java), REQ_SETUP)
        }
        lockNow = button("Lock now", false) {
            Parental.lock()
            onResume()
        }
        col.addView(
            cardBox(
                text("Parental control", 17f, ink, bold = true),
                parentNote,
                childRow,
                parentSetup,
                lockNow
            )
        )

        activityToday = text("Today: nothing hidden yet", 15f, ink, bold = true)
        activityBreak = text("", 13f, sub)
        activityApps = text("", 13f, sub)
        activityBars = WeekBars(this)
        col.addView(
            cardBox(
                text("Activity", 17f, ink, bold = true),
                text("Counts only. Nothing leaves this phone.", 13f, sub),
                activityToday,
                activityBreak,
                activityApps,
                activityBars.apply { layoutParams = LinearLayout.LayoutParams(-1, dp(72)).apply { topMargin = dp(8) } }
            )
        )

        protection = Switch(this)
        protectionNote = text("", 13f, sub)
        col.addView(
            cardBox(
                LinearLayout(this).apply {
                    orientation = LinearLayout.HORIZONTAL
                    gravity = Gravity.CENTER_VERTICAL
                    addView(
                        LinearLayout(context).apply {
                            orientation = LinearLayout.VERTICAL
                            addView(text("Protection", 20f, ink, bold = true))
                            addView(protectionNote)
                        },
                        LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
                    )
                    addView(protection)
                }
            )
        )
        protection.setOnCheckedChangeListener { sw, on -> if (sw.isPressed) setProtection(on) }

        nudity = Switch(this)
        nudity.setOnCheckedChangeListener { sw, on ->
            if (!sw.isPressed) return@setOnCheckedChangeListener
            if (Parental.childMode(this)) return@setOnCheckedChangeListener
            VeilSettings.setNudity(this, on)
            GuardRuntime.reloadLanes()
            refresh()
        }
        val always = cardBox(text("Always hidden", 17f, ink, bold = true))
        alwaysNote = text("Locked in child mode", 13f, sub)
        always.addView(alwaysNote)
        always.addView(switchRow("Nudity & explicit content", "Detected on the phone and blurred", nudity))
        for (p in WordLibrary.PACKS) {
            val sw = Switch(this)
            packSwitches[p.id] = sw
            sw.setOnCheckedChangeListener { s, on ->
                if (!s.isPressed) return@setOnCheckedChangeListener
                if (Parental.childMode(this)) {
                    if (p.id == "politics") VeilSettings.setChildPolitics(this, on)
                } else {
                    VeilSettings.setAdultPack(this, p.id, on)
                }
                thread {
                    runCatching { WordLibrary.setPack(this, p, on) }
                    runOnUiThread { refresh() }
                }
            }
            always.addView(switchRow(p.name, p.note, sw))
        }
        col.addView(always)

        wordInput = EditText(this).apply {
            hint = "Type a word, e.g. bison"
            setSingleLine()
            inputType = InputType.TYPE_CLASS_TEXT
            imeOptions = EditorInfo.IME_ACTION_DONE
            setTextColor(ink)
            setHintTextColor(sub)
            setOnEditorActionListener { _, id, _ ->
                if (id == EditorInfo.IME_ACTION_DONE) {
                    addWord()
                    true
                } else {
                    false
                }
            }
        }
        addButton = button("Add", true) { addWord() }
        wordStatus = text("", 13f, sub)
        wordList = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        col.addView(
            cardBox(
                text("Your words", 17f, ink, bold = true),
                text("Anything you name is learned on this phone and blurred wherever it appears.", 13f, sub),
                LinearLayout(this).apply {
                    orientation = LinearLayout.HORIZONTAL
                    gravity = Gravity.CENTER_VERTICAL
                    setPadding(0, dp(8), 0, 0)
                    addView(wordInput, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
                    addView(View(context), LinearLayout.LayoutParams(dp(8), 1))
                    addView(addButton)
                },
                wordStatus,
                wordList
            )
        )

        modes = RadioGroup(this).apply {
            orientation = RadioGroup.HORIZONTAL
            for ((key, label) in listOf("light" to "Light", "balanced" to "Balanced", "strict" to "Strict")) {
                addView(
                    RadioButton(context).apply {
                        text = label
                        tag = key
                        setTextColor(ink)
                        id = View.generateViewId()
                    }
                )
            }
            setOnCheckedChangeListener { g, checked ->
                val m = g.findViewById<RadioButton>(checked)?.tag as? String ?: return@setOnCheckedChangeListener
                if (m == VeilSettings.mode(this@MainActivity)) return@setOnCheckedChangeListener
                VeilSettings.setMode(this@MainActivity, m)
                if (VeilSettings.protectionOn(this@MainActivity)) command("mode", m)
            }
        }
        col.addView(
            cardBox(
                text("Sensitivity", 17f, ink, bold = true),
                text("Light hides only clear matches; Strict hides anything that might match.", 13f, sub),
                modes
            )
        )
        coverModes = RadioGroup(this).apply {
            orientation = RadioGroup.VERTICAL
            for ((full, label) in listOf(true to "Whole picture or video", false to "Just the object")) {
                addView(
                    RadioButton(context).apply {
                        text = label
                        tag = full
                        setTextColor(ink)
                        id = View.generateViewId()
                    }
                )
            }
            setOnCheckedChangeListener { g, checked ->
                val full = g.findViewById<RadioButton>(checked)?.tag as? Boolean ?: return@setOnCheckedChangeListener
                if (full == VeilSettings.fullCover(this@MainActivity)) return@setOnCheckedChangeListener
                VeilSettings.setFullCover(this@MainActivity, full)
                GuardRuntime.reloadLanes()
            }
        }
        col.addView(
            cardBox(
                text("How to hide", 17f, ink, bold = true),
                text(
                    "Whole picture or video covers everything the match appears in. Just the object covers only " +
                        "the matching thing and leaves the rest of the picture visible.",
                    13f,
                    sub
                ),
                coverModes
            )
        )
        col.addView(
            text("Nothing leaves this phone. Covers never block taps or scrolling.", 12f, sub).apply {
                setPadding(dp(4), dp(16), dp(4), 0)
            }
        )
        col.addView(
            text("🔒 All AI runs on this phone · 0 bytes sent", 12f, sub, bold = true).apply {
                setPadding(dp(4), dp(6), dp(4), dp(8))
            }
        )

        return ScrollView(this).apply {
            content = col
            setBackgroundColor(bg)
            addView(col)
            setOnApplyWindowInsetsListener { v, insets ->
                val b = insets.getInsets(WindowInsets.Type.systemBars() or WindowInsets.Type.ime())
                v.setPadding(b.left, b.top, b.right, b.bottom)
                insets
            }
        }
    }

    // ---- state ----

    private fun accessibilityOn(): Boolean {
        val s = Settings.Secure.getString(contentResolver, Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES)
            ?: return false
        return s.split(':').any { it.startsWith("$packageName/") && it.endsWith("GuardAccessibilityService") }
    }

    /** Fills the Activity card off the main thread (counts only). */
    private fun refreshActivity() {
        thread {
            val week = runCatching { com.veil.guard.app.ActivityStats.last7Days(this) }.getOrNull() ?: return@thread
            val today = week.last()
            val total = today.byCategory.values.sum()
            val names = mapOf(
                "nudity" to "nudity",
                "sexual" to "sexual",
                "violence" to "violence",
                "politics" to "political",
                "word" to "your words"
            )
            val parts = today.byCategory.entries.sortedByDescending { it.value }
                .joinToString(" · ") { "${it.value} ${names[it.key] ?: it.key}" }
            val system = setOf("com.android.systemui", "unknown", packageName)
            val apps = com.veil.guard.app.StatsCore.topApps(today, 8)
                .filter { (pkg, _) ->
                    pkg !in system &&
                        listOf("launcher", "uikit", "systemui").none { pkg.contains(it) }
                }
                .take(3)
                .joinToString(" · ") { (pkg, n) ->
                    val label = runCatching {
                        packageManager.getApplicationLabel(packageManager.getApplicationInfo(pkg, 0)).toString()
                    }.getOrDefault(pkg.substringAfterLast('.').replaceFirstChar { it.uppercase() })
                    "$label $n"
                }
            val bars = week.map { d -> d.byCategory.values.sum() }
            runOnUiThread {
                activityToday.text = if (total == 0) "Today: nothing hidden yet" else "Today: $total items hidden"
                activityBreak.text = parts
                activityBreak.visibility = if (parts.isEmpty()) View.GONE else View.VISIBLE
                activityApps.text = if (apps.isEmpty()) "" else "Most in: $apps"
                activityApps.visibility = if (apps.isEmpty()) View.GONE else View.VISIBLE
                activityBars.set(bars)
            }
        }
    }

    /** Seven small bars, oldest to today (today highlighted). */
    private class WeekBars(ctx: android.content.Context) : View(ctx) {
        private var values: List<Int> = List(7) { 0 }
        private val paint = android.graphics.Paint(android.graphics.Paint.ANTI_ALIAS_FLAG)

        fun set(v: List<Int>) {
            values = v
            invalidate()
        }

        override fun onDraw(canvas: android.graphics.Canvas) {
            val n = values.size.coerceAtLeast(1)
            val max = (values.maxOrNull() ?: 0).coerceAtLeast(1)
            val gap = width / (n * 4f)
            val bw = (width - gap * (n + 1)) / n
            for ((i, v) in values.withIndex()) {
                val h = (height - 4f) * v / max
                val x = gap + i * (bw + gap)
                paint.color = if (i == n - 1) 0xFF4A6CF7.toInt() else 0xFFC9D2F5.toInt()
                val top = if (v == 0) height - 4f else height - h.coerceAtLeast(4f)
                canvas.drawRoundRect(x, top, x + bw, height.toFloat(), 8f, 8f, paint)
            }
        }
    }

    private fun refresh() {
        refreshActivity()
        val a11y = accessibilityOn()
        setupCard.visibility = if (a11y) View.GONE else View.VISIBLE
        val on = VeilSettings.protectionOn(this) && a11y
        protection.isChecked = on
        val child = Parental.childMode(this)
        val hasPin = Parental.hasPin(this)
        protection.isEnabled = a11y
        lockedLook(protection, child)
        parentSetup.visibility = if (hasPin) View.GONE else View.VISIBLE
        childRow.visibility = if (hasPin) View.VISIBLE else View.GONE
        lockNow.visibility = if (hasPin) View.VISIBLE else View.GONE
        childSwitch.isChecked = child
        parentNote.text = when {
            !hasPin -> "Set a parent PIN to protect these settings and hide content for a child."
            child -> "Child mode on: the child cannot change these settings"
            else -> "Adult mode"
        }
        alwaysNote.visibility = if (child) View.VISIBLE else View.GONE
        lockedLook(nudity, child)
        val topics = WordLibrary.words(this).size + activeDefaults()
        protectionNote.text = when {
            !a11y -> "Finish setup to turn Veil on"
            on -> "On · hiding $topics topics"
            else -> "Off"
        }
        nudity.isChecked = VeilSettings.nudity(this)
        for (p in WordLibrary.PACKS) {
            packSwitches[p.id]?.apply {
                isChecked = WordLibrary.packOn(this@MainActivity, p)
                lockedLook(this, child && p.id != "politics")
            }
        }
        val m = VeilSettings.mode(this)
        for (i in 0 until modes.childCount) {
            val rb = modes.getChildAt(i) as RadioButton
            if (rb.tag == m && !rb.isChecked) rb.isChecked = true
        }
        val full = VeilSettings.fullCover(this)
        for (i in 0 until coverModes.childCount) {
            val rb = coverModes.getChildAt(i) as RadioButton
            if (rb.tag == full && !rb.isChecked) rb.isChecked = true
        }
        renderWords()
    }

    /** Locked switches keep their real on/off look (a disabled switch looks "off" on some phones) but ignore taps. */
    private fun lockedLook(s: Switch, locked: Boolean) {
        s.isClickable = !locked
        s.alpha = if (locked) 0.6f else 1f
    }

    private fun activeDefaults() =
        (if (VeilSettings.nudity(this)) 1 else 0) + WordLibrary.PACKS.count { WordLibrary.packOn(this, it) }

    private fun renderWords() {
        wordList.removeAllViews()
        val words = WordLibrary.words(this)
        if (words.isEmpty()) {
            wordList.addView(text("No words yet.", 14f, sub).apply { setPadding(0, dp(10), 0, 0) })
        }
        for (w in words) {
            val state = if (WordLibrary.isActive(this, w.id)) "Blurred wherever it appears" else "Could not load"
            wordList.addView(
                LinearLayout(this).apply {
                    orientation = LinearLayout.HORIZONTAL
                    gravity = Gravity.CENTER_VERTICAL
                    setPadding(0, dp(10), 0, 0)
                    addView(
                        LinearLayout(context).apply {
                            orientation = LinearLayout.VERTICAL
                            addView(text(w.name, 16f, ink, bold = true))
                            addView(text(state, 12f, sub))
                        },
                        LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
                    )
                    addView(
                        button("Remove", false) {
                            WordLibrary.remove(this@MainActivity, w.id)
                            refresh()
                        }
                    )
                }
            )
        }
    }

    private fun firstRun() {
        thread {
            if (!VeilSettings.seeded(this) || VeilSettings.packsVersion(this) < PACKS_VERSION) {
                runCatching { WordLibrary.PACKS.forEach { WordLibrary.setPack(this, it, true) } }
                runCatching { WordLibrary.ensureBank(this) }
                VeilSettings.setSeeded(this)
                VeilSettings.setPacksVersion(this, PACKS_VERSION)
            }
            runCatching { WordLibrary.syncProfile(this) }
            runOnUiThread { refresh() }
        }
    }

    // ---- actions ----

    private fun addWord() {
        val word = wordInput.text.toString().trim()
        if (word.isEmpty()) return
        (getSystemService(INPUT_METHOD_SERVICE) as InputMethodManager).hideSoftInputFromWindow(wordInput.windowToken, 0)
        addButton.isEnabled = false
        wordStatus.text = "Learning “$word” on this phone…"
        thread {
            val r = runCatching { WordLibrary.learn(this, word) }
            runOnUiThread {
                addButton.isEnabled = true
                r.onSuccess {
                    wordInput.setText("")
                    wordStatus.text = "“$word” added. It will be blurred wherever it appears."
                }.onFailure { wordStatus.text = "Couldn't add “$word”: ${it.message}" }
                refresh()
            }
        }
    }

    private fun setProtection(on: Boolean) {
        if (on && !accessibilityOn()) {
            refresh()
            return
        }
        if (on && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 1)
        }
        VeilSettings.setProtectionOn(this, on)
        if (on) {
            command("source", "a11y")
            command("mode", VeilSettings.mode(this))
        } else {
            command("stop", null)
        }
        refresh()
    }

    private fun command(cmd: String, value: String?) {
        val i = Intent(this, CaptureService::class.java).apply {
            action = CaptureCommandReceiver.ACTION_CMD
            putExtra(CaptureCommandReceiver.EXTRA_CMD, cmd)
            if (value != null) putExtra(CaptureCommandReceiver.EXTRA_VALUE, value)
        }
        startForegroundService(i)
    }

    companion object {
        const val TAG = "VeilHello"
        private const val PACKS_VERSION = 4
        private const val REQ_UNLOCK = 1
        private const val REQ_SETUP = 2
    }
}
