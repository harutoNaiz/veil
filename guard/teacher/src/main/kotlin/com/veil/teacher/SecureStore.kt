package com.veil.teacher

import java.io.File
import java.nio.file.Files
import java.nio.file.StandardCopyOption
import java.security.SecureRandom
import javax.crypto.Cipher
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.SecretKeySpec
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject

/** AES-256-GCM encrypted JSON document {settings, cards, corrections}; file = IV(12) + ciphertext+tag. */
class SecureStore(private val file: File, private val keys: KeyProvider) {
    private val random = SecureRandom()

    private fun spec(): SecretKeySpec {
        val k = keys.key()
        require(k.size == 32) { "key must be 32 bytes" }
        return SecretKeySpec(k, "AES")
    }

    fun read(): JsonObject {
        if (!file.isFile) return empty()
        val raw = file.readBytes()
        val c = Cipher.getInstance("AES/GCM/NoPadding")
        c.init(Cipher.DECRYPT_MODE, spec(), GCMParameterSpec(TAG_BITS, raw.copyOfRange(0, IV)))
        val plain = c.doFinal(raw, IV, raw.size - IV) // wrong key: AEADBadTagException
        return Json.parseToJsonElement(String(plain, Charsets.UTF_8)) as JsonObject
    }

    fun write(doc: JsonObject) {
        val iv = ByteArray(IV).also(random::nextBytes)
        val c = Cipher.getInstance("AES/GCM/NoPadding")
        c.init(Cipher.ENCRYPT_MODE, spec(), GCMParameterSpec(TAG_BITS, iv))
        val bytes = iv + c.doFinal(doc.toString().toByteArray(Charsets.UTF_8))
        file.absoluteFile.parentFile?.mkdirs()
        val tmp = File(file.absolutePath + ".tmp")
        tmp.writeBytes(bytes)
        Files.move(tmp.toPath(), file.toPath(), StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE)
    }

    private fun empty() = JsonObject(
        mapOf(
            "settings" to JsonObject(emptyMap()),
            "cards" to JsonArray(emptyList()),
            "corrections" to JsonArray(emptyList())
        )
    )

    private companion object {
        const val IV = 12
        const val TAG_BITS = 128
    }
}
