package com.veil.guard.teacher

import android.app.Activity
import android.os.Bundle
import android.util.Log
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView
import com.veil.teacher.OrtTextEncoder
import com.veil.teacher.Teacher
import com.veil.teacher.TextTokenizer
import com.veil.teacher.autocal.AutoCal
import com.veil.teacher.autocal.BankFile
import com.veil.teacher.autocal.VocabFile
import java.io.File
import kotlin.concurrent.thread

/**
 * Text field to concept card; shows how long it took and writes the card JSON to app files.
 * The compile step needs the SigLIP2 text ONNX in filesDir/siglip2-text.onnx and a tokenizer;
 * the on-phone tokenizer is DEFERRED, so without one only the card is made.
 */
class TeacherDebugActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val input = EditText(this).apply { hint = "word, e.g. spiders" }
        val out = TextView(this)
        val go = Button(this).apply { text = "Make card" }
        setContentView(
            LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(PAD, PAD, PAD, PAD)
                addView(input)
                addView(go)
                addView(out)
            }
        )
        go.setOnClickListener {
            val word = input.text.toString()
            thread {
                val t0 = System.nanoTime()
                val card = Teacher.conceptCard(word)
                val model = File(filesDir, "siglip2-text.onnx")
                val tokenizer = TOKENIZER
                val md = File(externalMediaDirs.first(), "models")
                val bankF = File(md, "bank-v1.bin")
                val vocF = File(md, "vocab-v1.bin")
                val vocJ = File(md, "vocab-v1.json")
                val note =
                    if (bankF.isFile && vocF.isFile && vocJ.isFile) {
                        val enc = if (model.isFile && tokenizer != null) OrtTextEncoder(model.path, tokenizer) else null
                        val chips = runCatching {
                            AutoCal.compileAuto(
                                word,
                                emptyList(),
                                enc,
                                BankFile.load(bankF),
                                VocabFile.load(vocF, vocJ)
                            )
                                .second
                        }
                        enc?.close()
                        val ms0 = (System.nanoTime() - t0) / NS_PER_MS
                        Log.i("VeilTeacher", "ADD word=$word ms=$ms0 chips=${chips.getOrNull()}")
                        "auto-compiled chips=${chips.getOrNull()} err=${chips.exceptionOrNull()?.message}"
                    } else if (model.isFile && tokenizer != null) {
                        OrtTextEncoder(model.path, tokenizer).use { Teacher.compile(card, it) }
                        "compiled"
                    } else {
                        "card only (model/tokenizer not on device)"
                    }
                val ms = (System.nanoTime() - t0) / NS_PER_MS
                File(filesDir, "card-${card["conceptId"]}.json").writeText(Teacher.conceptSha256(card) + "\n" + card)
                runCatching {
                    val dir = File(externalMediaDirs.first(), "concepts").also { it.mkdirs() }
                    val tmp = File(dir, "${card["conceptId"]}.json.tmp")
                    tmp.writeText(card.toString())
                    tmp.renameTo(File(dir, "${card["conceptId"]}.json"))
                }
                runOnUiThread { out.text = "$note, ms=$ms\n$card" }
            }
        }
    }

    private companion object {
        const val PAD = 32
        const val NS_PER_MS = 1_000_000
        val TOKENIZER: TextTokenizer? = null // DEFERRED: on-phone SigLIP2 tokenizer
    }
}
