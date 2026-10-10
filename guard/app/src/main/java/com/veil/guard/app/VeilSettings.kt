package com.veil.guard.app

import android.content.Context

/** What the user chose in the app: protection on/off, the built-in categories and the sensitivity. */
object VeilSettings {
    private fun prefs(ctx: Context) = ctx.applicationContext.getSharedPreferences("veil_app", Context.MODE_PRIVATE)

    fun protectionOn(ctx: Context) = Parental.childMode(ctx) || prefs(ctx).getBoolean("protection", false)

    fun setProtectionOn(ctx: Context, on: Boolean) = prefs(ctx).edit().putBoolean("protection", on).apply()

    /** Built-in category "Nudity & explicit content" (the NudeNet layer). On by default. */
    fun nudity(ctx: Context) = Parental.childMode(ctx) || adultNudity(ctx)

    fun adultNudity(ctx: Context) = prefs(ctx).getBoolean("cat_nudity", true)

    /** Whether the pack should be on in the current mode. Child: violence and sexual content always, politics per the parent. */
    fun packWanted(ctx: Context, id: String): Boolean = when {
        !Parental.childMode(ctx) -> prefs(ctx).getBoolean("adult_pack_$id", true)
        id == "politics" -> prefs(ctx).getBoolean("child_pack_politics", true)
        else -> true
    }

    fun setAdultPack(ctx: Context, id: String, on: Boolean) = prefs(ctx).edit().putBoolean("adult_pack_$id", on).apply()

    fun setChildPolitics(ctx: Context, on: Boolean) = prefs(ctx).edit().putBoolean("child_pack_politics", on).apply()

    fun setNudity(ctx: Context, on: Boolean) = prefs(ctx).edit().putBoolean("cat_nudity", on).apply()

    /** light | balanced | strict */
    fun mode(ctx: Context) = prefs(ctx).getString("mode", "balanced") ?: "balanced"

    fun setMode(ctx: Context, m: String) = prefs(ctx).edit().putString("mode", m).apply()

    /** How to hide: true = the whole picture or video (default), false = just the detected object. */
    fun fullCover(ctx: Context) = prefs(ctx).getBoolean("full_cover", true)

    fun setFullCover(ctx: Context, on: Boolean) = prefs(ctx).edit().putBoolean("full_cover", on).apply()

    /** First launch seeds the default categories once; the user can switch them off afterwards. */
    fun seeded(ctx: Context) = prefs(ctx).getBoolean("seeded", false)

    fun setSeeded(ctx: Context) = prefs(ctx).edit().putBoolean("seeded", true).apply()

    /** Built-in pack contents version: a newer app re-installs the packs once. */
    fun packsVersion(ctx: Context) = prefs(ctx).getInt("packs_version", 1)

    fun setPacksVersion(ctx: Context, v: Int) = prefs(ctx).edit().putInt("packs_version", v).apply()
}
