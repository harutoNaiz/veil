package com.veil.guard.teacher

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import com.veil.teacher.KeyProvider
import java.io.File
import java.security.KeyStore
import java.security.SecureRandom
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/**
 * The 32-byte store key is random, kept in a file that is wrapped (AES-GCM) by a non-exportable
 * Android Keystore key. The file alone is useless off the device.
 */
class KeystoreKeyProvider(context: Context) : KeyProvider {
    private val file = File(context.filesDir, "veil-store.key")

    private fun wrapKey(): SecretKey {
        val ks = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (ks.getKey(ALIAS, null) as? SecretKey)?.let { return it }
        val gen = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
        gen.init(
            KeyGenParameterSpec.Builder(ALIAS, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .build()
        )
        return gen.generateKey()
    }

    @Synchronized
    override fun key(): ByteArray {
        val wrap = wrapKey()
        if (file.isFile) {
            val raw = file.readBytes()
            val c = Cipher.getInstance("AES/GCM/NoPadding")
            c.init(Cipher.DECRYPT_MODE, wrap, GCMParameterSpec(TAG_BITS, raw.copyOfRange(0, IV)))
            return c.doFinal(raw, IV, raw.size - IV)
        }
        val fresh = ByteArray(KEY_BYTES).also(SecureRandom()::nextBytes)
        val c = Cipher.getInstance("AES/GCM/NoPadding")
        c.init(Cipher.ENCRYPT_MODE, wrap)
        file.writeBytes(c.iv + c.doFinal(fresh))
        return fresh
    }

    private companion object {
        const val ALIAS = "veil-store-wrap"
        const val IV = 12
        const val TAG_BITS = 128
        const val KEY_BYTES = 32
    }
}
