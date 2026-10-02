**Problem**
Users are exposed to explicit, abusive, or manipulated images and video before they can choose to engage. Cloud-based moderation adds latency and requires sending sensitive content off the device.

**Solution**
An on-device safety layer on a Snapdragon Android phone that analyzes screen content in real time and blurs, masks, or blocks harmful material before the user sees it. Nothing leaves the phone.

**How to build it in a week**
- **Models:** Pretrained small vision models (not Gemma/Qwen), with a thin fine-tuned head only if needed.
- **Pipeline:** Screen capture → fast NSFW classifier → if flagged, region detector (e.g., NudeNet) → blur those boxes via an overlay.
- **Extras:** OCR + small toxicity classifier for abusive text; a deepfake "risk score" from an open detector.
- **Runtime:** ExecuTorch with the Qualcomm QNN backend on the NPU.

**Main risks**
- ExecuTorch/QNN export (do this first)
- False positives eroding trust
- Battery, permissions, and Play Store policy

**Plan:** Days 1-2 export and benchmark a model; Day 3 capture and overlay; Day 4 region blurring; Day 5 text detection; Days 6-7 tuning and demo.