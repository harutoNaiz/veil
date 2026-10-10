package com.veil.guard.app

import android.content.Context
import com.veil.guard.wire.ml.LazyTextEncoder
import com.veil.guard.wire.ml.ModelStore
import com.veil.teacher.Teacher
import com.veil.teacher.autocal.AutoCal
import com.veil.teacher.autocal.BankFile
import com.veil.teacher.autocal.VocabFile
import java.io.File
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

/**
 * The block list on disk. Every entry is a compiled concept JSON in the guard's concepts folder, which the running
 * guard watches and reloads: adding a word = learning it on the phone (AutoCal against the bundled reference bank)
 * and writing the result there; removing it = deleting the file. Built-in packs ship compiled in the app assets.
 */
object WordLibrary {
    data class Entry(val id: String, val name: String, val builtIn: Boolean)

    /** Built-in packs: a folder of compiled concepts under assets/packs/<id>/, switched on and off together. */
    val PACKS = listOf(
        Pack("politics", "Political content", "Political words, politicians, rallies, elections"),
        Pack("violence", "Violence & gore", "Gore, wounds, dead bodies, violent scenes"),
        Pack("sexual", "Sexual & suggestive content", "Intimate scenes, kissing, lingerie, swimwear")
    )

    data class Pack(val id: String, val name: String, val note: String)

    private fun packFile(ctx: Context, p: Pack, asset: String) = File(conceptsDir(ctx), "${p.id}--$asset")

    private val BANK_FILES = listOf("bank-v1.bin", "vocab-v1.bin", "vocab-v1.json")

    fun conceptsDir(ctx: Context) = File(ctx.externalMediaDirs.first(), "concepts").also { it.mkdirs() }

    private fun bankDir(ctx: Context) = File(ctx.filesDir, "bank").also { it.mkdirs() }

    /** The user's own words (everything in the folder that is not a built-in pack), sorted by name. */
    fun words(ctx: Context): List<Entry> = (conceptsDir(ctx).listFiles { f -> f.extension == "json" } ?: emptyArray())
        .map { it.nameWithoutExtension }
        .filter { !it.contains("--") && it != "politics" }
        .sorted()
        .map { Entry(it, it.replace('-', ' '), builtIn = false) }

    fun packOn(ctx: Context, p: Pack) =
        (conceptsDir(ctx).listFiles() ?: emptyArray()).any { it.name.startsWith("${p.id}--") }

    fun setPack(ctx: Context, p: Pack, on: Boolean) {
        File(conceptsDir(ctx), "${p.id}.json").delete() // pre-pack single file
        val assets = ctx.assets.list("packs/${p.id}").orEmpty().filter { it.endsWith(".json") }
        for (a in assets) {
            val f = packFile(ctx, p, a)
            if (on) {
                atomicWrite(
                    f,
                    ctx.assets.open("packs/${p.id}/$a").use {
                        it.readBytes()
                    }.decodeToString()
                )
            } else {
                f.delete()
            }
        }
    }

    fun remove(ctx: Context, id: String) {
        File(conceptsDir(ctx), "$id.json").delete()
        File(profileDir(ctx, activeProfile(ctx)), "$id.json").delete()
    }

    // ---- child / adult profiles ----

    fun activeProfile(ctx: Context) = if (Parental.childMode(ctx)) "child" else "adult"

    fun profileDir(ctx: Context, name: String) = File(ctx.filesDir, "profiles/$name").also { it.mkdirs() }

    private fun userFiles(dir: File): List<File> =
        (dir.listFiles { f -> f.extension == "json" } ?: emptyArray()).filter { !it.name.contains("--") }

    /**
     * Makes the guard's concepts folder match the active mode: the active profile's own words, and the built-in
     * packs as that mode wants them. First run moves the words already on the phone into the adult profile.
     */
    @Synchronized
    fun syncProfile(ctx: Context) {
        val adult = profileDir(ctx, "adult")
        profileDir(ctx, "child")
        val marker = File(ctx.filesDir, "profiles/.migrated")
        if (!marker.exists()) {
            userFiles(conceptsDir(ctx)).forEach { it.copyTo(File(adult, it.name), overwrite = true) }
            marker.writeText("1")
        }
        userFiles(conceptsDir(ctx)).forEach { it.delete() }
        userFiles(profileDir(ctx, activeProfile(ctx))).forEach {
            it.copyTo(File(conceptsDir(ctx), it.name), overwrite = true)
        }
        for (p in PACKS) {
            val want = VeilSettings.packWanted(ctx, p.id)
            if (want != packOn(ctx, p)) setPack(ctx, p, want)
        }
    }

    /** Copies the bundled reference bank (needed to learn words) out of the APK once. */
    @Synchronized
    fun ensureBank(ctx: Context) {
        val stamp = File(bankDir(ctx), "installed.stamp")
        val want = ctx.packageManager.getPackageInfo(ctx.packageName, 0).lastUpdateTime.toString()
        if (stamp.isFile && stamp.readText() == want && BANK_FILES.all { File(bankDir(ctx), it).isFile }) return
        for (name in BANK_FILES) {
            val dst = File(bankDir(ctx), name)
            val tmp = File(dst.path + ".tmp")
            ctx.assets.open("bank/$name").use { i -> tmp.outputStream().use { o -> i.copyTo(o) } }
            dst.delete()
            tmp.renameTo(dst)
        }
        stamp.writeText(want)
    }

    /**
     * Learns [word] on the phone and adds it to the block list. Returns the concept id. Words in the bank's
     * vocabulary need no model; any other word is encoded with the on-phone SigLIP2 text model.
     */
    fun learn(ctx: Context, word: String): String {
        val text = word.trim()
        require(text.isNotEmpty()) { "Type a word first" }
        ensureBank(ctx)
        val dir = bankDir(ctx)
        val bank = BankFile.load(File(dir, "bank-v1.bin"))
        val vocab = VocabFile.load(File(dir, "vocab-v1.bin"), File(dir, "vocab-v1.json"))
        val lazy = LazyTextEncoder(ModelStore(ctx))
        val cc = try {
            AutoCal.compileAuto(text, emptyList(), if (lazy.available()) lazy else null, bank, vocab).first
        } finally {
            lazy.close()
        }
        val id = Teacher.conceptCard(text)["conceptId"] as String
        val json = toJson(cc.raw).toString()
        atomicWrite(File(profileDir(ctx, activeProfile(ctx)), "$id.json"), json)
        atomicWrite(File(conceptsDir(ctx), "$id.json"), json)
        return id
    }

    /** True if the word file exists and parses (used to show "active"). */
    fun isActive(ctx: Context, id: String): Boolean = runCatching {
        Json.parseToJsonElement(File(conceptsDir(ctx), "$id.json").readText()).jsonObject["conceptId"]
            ?.jsonPrimitive?.content == id
    }.getOrDefault(false)

    private fun atomicWrite(f: File, text: String) {
        val tmp = File(f.path + ".tmp")
        tmp.writeText(text)
        if (!tmp.renameTo(f)) {
            f.delete()
            tmp.renameTo(f)
        }
    }

    fun toJson(v: Any?): JsonElement = when (v) {
        null -> JsonNull
        is JsonElement -> v
        is Map<*, *> -> JsonObject(v.entries.associate { it.key.toString() to toJson(it.value) })
        is Iterable<*> -> JsonArray(v.map { toJson(it) })
        is Array<*> -> JsonArray(v.map { toJson(it) })
        is DoubleArray -> JsonArray(v.map { JsonPrimitive(it) })
        is FloatArray -> JsonArray(v.map { JsonPrimitive(it) })
        is IntArray -> JsonArray(v.map { JsonPrimitive(it) })
        is Boolean -> JsonPrimitive(v)
        is Number -> JsonPrimitive(v)
        else -> JsonPrimitive(v.toString())
    }
}
