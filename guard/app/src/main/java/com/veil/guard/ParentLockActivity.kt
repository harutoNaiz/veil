package com.veil.guard

import android.app.Activity
import android.content.res.Configuration
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.text.InputType
import android.util.TypedValue
import android.view.Gravity
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView
import com.veil.guard.app.Parental

/**
 * The parent PIN screen. With no PIN yet it asks to set one (enter + confirm, at least 4 digits); otherwise it asks
 * for the PIN. Finishes with RESULT_OK once the PIN is set or correct, RESULT_CANCELED on back.
 */
class ParentLockActivity : Activity() {
    private val night get() =
        resources.configuration.uiMode and Configuration.UI_MODE_NIGHT_MASK == Configuration.UI_MODE_NIGHT_YES
    private val bg get() = if (night) 0xFF121417.toInt() else 0xFFF4F5F8.toInt()
    private val card get() = if (night) 0xFF1E2126.toInt() else Color.WHITE
    private val ink get() = if (night) 0xFFECEFF3.toInt() else 0xFF1B1E23.toInt()
    private val sub get() = if (night) 0xFF9AA1AB.toInt() else 0xFF5F6670.toInt()
    private val accent = 0xFF3B6FE0.toInt()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val setting = !Parental.hasPin(this)
        val pin = field(if (setting) "New PIN (4+ digits)" else "PIN")
        val confirm = field("Confirm PIN")
        val msg = label("", 13f, 0xFFD64545.toInt())
        val go = Button(this).apply {
            text = if (setting) "Set PIN" else "Unlock"
            isAllCaps = false
            setTextColor(Color.WHITE)
            background = GradientDrawable().apply {
                setColor(accent)
                cornerRadius = dp(12).toFloat()
            }
            setOnClickListener {
                val p = pin.text.toString()
                when {
                    setting && p.length < MIN_PIN -> msg.text = "Use at least $MIN_PIN digits"

                    setting && p != confirm.text.toString() -> msg.text = "The PINs don't match"

                    setting -> done { Parental.setPin(this@ParentLockActivity, p) }

                    !Parental.checkPin(this@ParentLockActivity, p) -> {
                        msg.text = "Wrong PIN"
                        pin.setText("")
                    }

                    else -> done { }
                }
            }
        }
        val box = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(18), dp(18), dp(18))
            background = GradientDrawable().apply {
                setColor(card)
                cornerRadius = dp(18).toFloat()
            }
            addView(label(if (setting) "Set a parent PIN" else "Enter parent PIN", 20f, ink, true))
            addView(
                label(
                    if (setting) {
                        "Only you will be able to change Veil's settings. Choose a PIN your child won't guess."
                    } else {
                        "Veil is locked by a parent PIN."
                    },
                    14f,
                    sub
                )
            )
            addView(pin)
            if (setting) addView(confirm)
            addView(msg)
            addView(go)
        }
        setContentView(
            LinearLayout(this).apply {
                setBackgroundColor(bg)
                gravity = Gravity.CENTER
                setPadding(dp(18), dp(18), dp(18), dp(18))
                addView(box, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, -2))
            }
        )
    }

    private fun done(save: () -> Unit) {
        save()
        setResult(RESULT_OK)
        finish()
    }

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        setResult(RESULT_CANCELED)
        finish()
    }

    private fun dp(v: Int) =
        TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, v.toFloat(), resources.displayMetrics).toInt()

    private fun label(s: String, size: Float, color: Int, bold: Boolean = false) = TextView(this).apply {
        text = s
        textSize = size
        setTextColor(color)
        if (bold) typeface = Typeface.DEFAULT_BOLD
        setPadding(0, 0, 0, dp(6))
    }

    private fun field(hintText: String) = EditText(this).apply {
        hint = hintText
        setSingleLine()
        inputType = InputType.TYPE_CLASS_NUMBER or InputType.TYPE_NUMBER_VARIATION_PASSWORD
        setTextColor(ink)
        setHintTextColor(sub)
    }

    private companion object {
        const val MIN_PIN = 4
    }
}
