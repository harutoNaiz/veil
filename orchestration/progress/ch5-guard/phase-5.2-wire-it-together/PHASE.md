# Phase 5.2 Wire it together · WAITING_HUMAN
Commits: 77a6c02 (5.2.1), f806915 (5.2.2), a6de352 (5.2.3), bd16085 (5.2-W.1), aec978e (5.2-W.2), 2ab2d60 (5.2-W.3) · Spec: SPEC.md (104 lines), SPEC-W.md (94 lines)

## Summary
- **5.2.1:** a new module, guard/conductor, with Ports, Conductor (never queues), Thumbs and Replay, plus a debug ReplayActivity. Replay parity against the twin: feed-scroll 449 masks at 100.0%, reels 79 at 100.0%, video 0 masks. The synth set was skipped because it is absent.
- **5.2.2:** RegionProposer, RegionLane and Hashes (dHash 9x8, not bit-exact pHash, deferred by the spec), plus workshop/guardcheck/cat_feed.py and pt-5.2.ps1.
- **5.2.3:** Layer1Lane with NudeDecode, TextLane, and MlKitOcr in the app. NudeNet layer-1 classes are indices 2, 3, 4, 6, 14 of the standard v3 18-label order.

## Deviations
- Ports.kt `Finder` is a `fun interface`.
- Conductor exposes `lastPlan` and `inject(Record)`.
- cat_feed.py accepts plan lines either flat or nested under "plan".

## Live wiring (5.2-W, SPEC-W.md): built
- **W.1:** GuardRuntime, GuardCore, ThreadWorker, StageTracker and JsonlDebugLog. CaptureService now creates the frame source and accepts the commands `mode`, `skip`, `concepts` and `status`. It also adds the asset `params.json` (same SHA as the twin's).
- **W.2:** FrameAdapter, plus the real ONNX adapters. SigLIP2 is the Describer and NudeNet is Layer 1. Also ConceptPack and LiveLanes. Models are read from `<media>/models`, concepts from `<media>/concepts/*.json`. These are compile-checked only on the laptop.
- **W.3:** GuardAccessibilityService now hosts the OverlayRenderer, SelfCapture, GlueController and CoverTouchLayer. Also EventAdapter, PlanRecords, LayoutFeed, LiveOverlay, and a `veil.draw` Trace section.
- **Deferred:** D-5.2W-* (Finder, toxicity tokenizer, Teacher swap, accelerators, console backend, tune sync).

## Human
HC-026, after 5.2-W.
