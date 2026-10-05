# Known issues

- **D-6.3-guard (Deferred, D2):** Kotlin crash and restart tests (START_STICKY, Resume notification) need Gradle and a phone (5.2). Recovery is proved only against FakeGuard.
- **D-6.3-blind (Deferred, D3):** the "can't see protected video" hint is a Guard overlay (Kotlin, needs 5.2).
- **D-6.1-apk (Deferred):** the 6.1 APK compile is deferred; no on-phone build exists yet.
- **Protected video is not seen:** apps that block screen capture (for example Netflix) show a black frame, so Veil cannot cover their content.
