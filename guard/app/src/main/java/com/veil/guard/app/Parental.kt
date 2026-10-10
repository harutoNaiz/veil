package com.veil.guard.app

import android.content.Context
import android.os.SystemClock
import java.security.MessageDigest
import java.security.SecureRandom

/**
 * Parental control state, shared by the app screen, the overlay and the tamper guard.
 *
 * - The parent sets a PIN once. With a PIN set, the Veil app opens behind the PIN screen.
 * - Child mode (parental control): built-in categories are forced on, the child's own word list applies, labels
 *   never name nudity or gore, covers cannot be revealed, and Veil cannot be turned off, changed or uninstalled
 *   without the PIN.
 * - Adult mode (child mode off, switched by the parent with the PIN): the adult's word list and toggles apply, and
 *   a consenting adult may tap "Continue" on a cover to see what is behind it.
 * - Unlocking (correct PIN) opens a short session so the parent is not asked again on every screen.
 */
object Parental {
    private const val PREFS = "veil_parent"
    private const val SESSION_MS = 5 * 60 * 1000L

    @Volatile private var unlockedUntil = 0L

    private fun prefs(ctx: Context) = ctx.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    /** True once the parent has chosen a PIN. */
    fun hasPin(ctx: Context): Boolean = prefs(ctx).contains("pin_hash")

    fun setPin(ctx: Context, pin: String) {
        require(pin.length >= 4) { "PIN must have at least 4 digits" }
        val salt = ByteArray(16).also { SecureRandom().nextBytes(it) }
        prefs(ctx).edit().putString("pin_salt", hex(salt)).putString("pin_hash", hash(salt, pin)).apply()
        unlock()
    }

    /** Checks [pin]; a correct PIN also opens the unlock session. */
    fun checkPin(ctx: Context, pin: String): Boolean {
        val p = prefs(ctx)
        val salt = p.getString("pin_salt", null) ?: return false
        val ok = MessageDigest.isEqual(
            hash(unhex(salt), pin).toByteArray(),
            (p.getString("pin_hash", "") ?: "").toByteArray()
        )
        if (ok) unlock()
        return ok
    }

    fun unlock() {
        unlockedUntil = SystemClock.elapsedRealtime() + SESSION_MS
    }

    fun lock() {
        unlockedUntil = 0L
    }

    /** No PIN set (nothing to protect) or a correct PIN was entered in the last few minutes. */
    fun isUnlocked(ctx: Context): Boolean = !hasPin(ctx) || SystemClock.elapsedRealtime() < unlockedUntil

    /** Child mode (parental control). Only meaningful with a PIN; without one the phone is in adult mode. */
    fun childMode(ctx: Context): Boolean = hasPin(ctx) && prefs(ctx).getBoolean("child_mode", true)

    fun setChildMode(ctx: Context, on: Boolean) = prefs(ctx).edit().putBoolean("child_mode", on).apply()

    /** "Continue" on a cover: only for a consenting adult, i.e. adult mode with the parent PIN set up. */
    fun revealAllowed(ctx: Context): Boolean = hasPin(ctx) && !childMode(ctx)

    /** Settings and uninstall are protected while in child mode and not unlocked. */
    fun tamperGuarded(ctx: Context): Boolean = childMode(ctx) && !isUnlocked(ctx)

    private fun hash(salt: ByteArray, pin: String): String =
        hex(MessageDigest.getInstance("SHA-256").digest(salt + pin.toByteArray()))

    private fun hex(b: ByteArray) = b.joinToString("") { "%02x".format(it) }

    private fun unhex(s: String) = ByteArray(s.length / 2) { s.substring(it * 2, it * 2 + 2).toInt(16).toByte() }
}
