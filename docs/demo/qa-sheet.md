# Q&A sheet

Numbers are cited from the final report or marked PENDING-HUMAN.

## Battery
- Q: What does it cost? A: Light, Balanced and Strict differ. Balanced battery use per hour: PENDING-HUMAN [F-02]. Strict costs more; we say so on stage.

## Privacy
- Q: Does anything leave the phone? A: No. Frames are analysed on the device and dropped. Airplane mode is part of the demo. Recordings and labels stay in a git-ignored folder.

## False covers
- Q: What if it covers the wrong thing? A: Tap "Not a cat" (or the matching word). The correction is stored on the phone and the cover is lifted. Rates are in the final report: PENDING-HUMAN.

## Play Store path
- Q: Can it ship? A: It needs the accessibility service, which Google Play restricts. Policy: https://support.google.com/googleplay/android-developer/answer/10964491. Store release is out of scope for now; the demo is a sideloaded build.

## Licences (Appendix C)
- **SigLIP2**: Apache-2.0. Fine for commercial use.
- **YOLOE (Ultralytics)**: AGPL-3.0 (assumed; to verify). Commercial use needs an Ultralytics licence or a replacement. Demo and research use only.
- **MobileCLIP / MobileCLIP2 weights**: Apple research-only. Not usable in a commercial product, so they must be replaced before any release.
- **NudeNet**: AGPL-3.0 (reported; to verify). Needs replacement or compliance before release.
- **Toxicity model**: Apache-2.0 (mmBERT-small based). Fine for commercial use.
