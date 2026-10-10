package com.veil.guard.overlay

import android.content.Context
import android.media.AudioManager
import android.view.KeyEvent

/**
 * Keeps sound calm while a big cover (usually a video) is up. Adult mode: pause once per warning, resume on
 * Continue. Child mode: mute music while any big cover shows; always unmuted again when none remains.
 */
class MediaCalm(ctx: Context) {
    private val audio = ctx.getSystemService(Context.AUDIO_SERVICE) as? AudioManager
    private var known = emptySet<Int>()
    private val paused = HashSet<Int>()
    private var muted = false

    /** [big] = ids of big covers now on screen. */
    fun update(big: Set<Int>, adult: Boolean, child: Boolean) {
        val a = audio ?: return
        runCatching {
            if (child) {
                if (big.isNotEmpty() && !muted) {
                    a.adjustStreamVolume(AudioManager.STREAM_MUSIC, AudioManager.ADJUST_MUTE, 0)
                    muted = true
                }
            } else if (adult && (big - known).isNotEmpty() && a.isMusicActive) {
                key(a, KeyEvent.KEYCODE_MEDIA_PAUSE)
                paused.addAll(big - known)
            }
            if (muted && (big.isEmpty() || !child)) unmute(a)
        }
        paused.retainAll(big)
        known = big
    }

    /** The user tapped Continue on cover [id]: resume what we paused for it. */
    fun onContinue(id: Int) {
        val a = audio ?: return
        if (paused.remove(id)) runCatching { key(a, KeyEvent.KEYCODE_MEDIA_PLAY) }
    }

    /** Overlay going away: never leave the phone muted. */
    fun release() {
        audio?.let { runCatching { if (muted) unmute(it) } }
        known = emptySet()
        paused.clear()
    }

    private fun unmute(a: AudioManager) {
        a.adjustStreamVolume(AudioManager.STREAM_MUSIC, AudioManager.ADJUST_UNMUTE, 0)
        muted = false
    }

    private fun key(a: AudioManager, code: Int) {
        a.dispatchMediaKeyEvent(KeyEvent(KeyEvent.ACTION_DOWN, code))
        a.dispatchMediaKeyEvent(KeyEvent(KeyEvent.ACTION_UP, code))
    }
}
