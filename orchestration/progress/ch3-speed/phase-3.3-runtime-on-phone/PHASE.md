# Phase 3.3 Runtime on the phone · WAITING_HUMAN
Commits: fda43f1 (3.3.1), 524b12a (3.3.2), 45eff08 (3.3.3, + manifest fix round) · Spec: SPEC.md (82 lines)

## Summary
- **3.3.1:** the smoketest APK and its test APK, built with ORT-QNN 1.29.0 (fallback off) and LiteRT 2.2.0. The APK contains libonnxruntime.so, libQnnHtp.so and 6 libQnnHtpV*Skel.so files, and the manifest declares libcdsprpc.so. The pt mode uses dummy inputs.
- **3.3.2:** guard/runtime, a pure-JVM layer: Api, Config, Latency, ProfileCheck, Resident and ImagePrep. Its ORT run options are `qnn.htp_perf_mode=burst` and `post_run=low_power_saver`.
- **3.3.3:** guard/soak analysers, the phone scripts under tools/phone/3.3 (install, bench, pt, soak), laptop_ref, a draft of docs/reports/ch3-speed.md, and decision D-3.3 (a draft).
- Everything on the phone is PENDING-HUMAN (HC-027), including the Chapter 3 gate.

## Deviations
- **litert and litert-api share a namespace.** guard/gradle.properties now sets `android.uniquePackageNames=false`.
- **The manifest schema is 3.3.1's own,** `{inputs, outputs:[{name, shape, dtype}]}`. The 3.3.3 fix round generates `<id>.manifest.json` from the exported ONNX files.
- **laptop_ref was run with only 2 images.** Run the full 50 before the phone sitting; it's step 1 of HC-027.
