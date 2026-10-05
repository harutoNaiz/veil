# Veil: Project Plan

Veil (working name) is an on-device screen filter for Android. It watches what is on screen, finds anything the user does not want to see (nudity and abuse by default, plus anything the user names, like "cats"), and covers it. Nothing on the screen ever leaves the phone.

This plan breaks the whole build into **6 chapters × 3 phases × 3 sub-phases**. It has no calendar. Each sub-phase says what to do, what it produces, and how you know it is done. Work moves forward when a "done when" check passes, not when a date arrives.

---

## How to read this plan

- **Chapters** are big goals that each answer one question ("Does the idea work?", "Is it fast enough?").
- **Phases** are the steps inside a chapter.
- **Sub-phases** are units of work one person can own and finish.
- **Proof test:** one end-to-end check per phase that proves the feature works the way a user would experience it. It runs on the real phone wherever possible, or on fresh real data for laptop-only phases. Unit tests don't count. See [Test bench](#test-bench-what-to-install-on-the-laptop).
- **Acceptance contract:** the agreed definition of "finished" at the end of every phase: what must exist, numbered checks with pass thresholds, who verifies, and what later phases may rely on. See [Acceptance contracts](#acceptance-contracts).
- **Chapter gate:** the check at the end of each chapter. Passing it means the next chapters can trust this one. Failing it triggers the listed fallback; it never means "stop the project". Each chapter gate is part of the acceptance contract of that chapter's last phase.
- **Numbers marked "target"** are proposals to agree as a team. Numbers marked "published" come from vendor benchmarks. Numbers marked "estimate" are worked out, not measured.

### The six chapters

| # | Chapter | The question it answers | Where it runs |
| --- | --- | --- | --- |
| 1 | SEE | Does "find what I hate and cover it" work on still screenshots? | Laptop |
| 2 | MOTION | Does it hold up on moving screens, without wasting effort or flickering? | Laptop |
| 3 | SPEED | Is the AI fast enough on the phone's AI chip? | Cloud phones, then the real phone |
| 4 | PLUMBING | Can the phone watch its own screen and draw covers on top? | Real phone |
| 5 | GUARD | Do chapters 2, 3 and 4 work together on the real phone? | Real phone |
| 6 | PRODUCT | Can a real user set it up, teach it, correct it, and trust it? | Real phone + server |

### What depends on what

```
  ┌──────────┐      ┌──────────┐
  │ 1  SEE   │─────▶│ 2 MOTION │──────────────┐
  └────┬─────┘      └──────────┘              │
       │ chosen models                        ▼
       │            ┌──────────┐        ┌──────────┐      ┌───────────┐
       └───────────▶│ 3  SPEED │───────▶│ 5  GUARD │─────▶│ 6 PRODUCT │
                    └──────────┘        └──────────┘      └───────────┘
                    ┌──────────┐              ▲                 ▲
                    │4 PLUMBING│──────────────┘                 │
                    └──────────┘                                │
        6.1 Console app can start at any time against a fake Guard
```

- Chapters 1, 3.3.1 (runtime smoke test), 4 and 6.1 can all **start on the first day of work**.
- Chapter 3 needs chapter 1's model choice for most of its work.
- Chapter 5 needs chapters 2, 3 and 4 to have passed their gates.

### Suggested owners (4 people)

| Person | Owns | Notes |
| --- | --- | --- |
| A: AI | Chapters 1 and 3 | Python, model export, Qualcomm AI Hub |
| B: Brain | Chapter 2, then porting it in 5.1 | Python first, then Kotlin |
| C: Phone | Chapter 4, then wiring in 5.2 and 5.3 | Kotlin, Android |
| D: App | Chapter 6.1 from day one, then 6.2 and 6.3 | Flutter, Flask |

### Plain-language glossary

| Word in this plan | What it means |
| --- | --- |
| Guard | The part that runs in the background on the phone and does all the watching and covering |
| Console | The Flutter app the user taps (settings, list of dislikes, stats) |
| Workshop | Our laptops/server (Python + Flask). Prepares AI models and topic packs. Never sees anyone's screen |
| Gatekeeper | Decides *when* to look at the screen (saves battery) |
| Spotter | Cuts the screen into pieces: posts, photos, objects inside photos, text |
| Describer | Turns each piece into a "meaning fingerprint" (a list of numbers; similar things get similar fingerprints) |
| Judge | Compares fingerprints with the user's list and decides "hide" or "leave" |
| Follower | Keeps each cover glued to its item while scrolling, and stops flicker |
| Painter | Draws the covers on top of other apps |
| Teacher | Turns a word like "cats" (and optional example photos) into a "concept card" the Judge can use |
| Concept card | The stored description of one dislike: what it looks like, lookalikes to ignore, strictness |
| Layer 1 | Always-on safety (nudity, abusive text). Built-in models, covers can't be peeked |
| Layer 2 | The user's own list (anything they name or show). Covers can be peeked |
| Look / burst | One run of the whole find → describe → judge chain on a screen frame |
| Twin | The Python copy of the Guard's decision logic, used on laptops to test and tune |
| Tape | A recorded input (frames + scroll events) and the expected output, used to check the phone and laptop versions behave identically |

### Fixed decisions this plan builds on

1. **Index and match.** Every visible piece of the screen gets a fingerprint; the user's dislikes are queries; similarity decides. Detectors only *propose* pieces.
2. **Look only on change.** Work follows how much new content appears, not the screen's frame rate.
3. **Separate units, shared contracts.** Every unit talks through simple, versioned JSON shapes, so each can be built and tested alone.
4. **Python twin first, phone second.** Logic is proven on recordings on a laptop, then ported to the phone and checked against the same tapes.
5. **Two layers.** Layer 1 is fixed and always on. Layer 2 is open: anything the user names.
6. **Starting technology** (can change at a gate): SigLIP2-B/16 as the Describer, YOLOE as the Spotter's object finder, NudeNet for Layer 1, ONNX Runtime with Qualcomm's QNN for the AI chip (LiteRT as fallback), Kotlin for the Guard, Flutter for the Console, Python + Flask for the Workshop.

### Proposed repository layout

```
veil/
  contracts/      JSON Schemas shared by every part (the "language" units speak)
  workshop/       Python: twin, evaluation, model export, Flask API
  guard/          Android (Kotlin): capture, accessibility, overlay, brain, AI runtime
  console/        Flutter app
  data/           screenshots, recordings, labels (private; not pushed to public remotes)
  docs/           decisions, device profile, reports, acceptance records
```

## Acceptance contracts

Every phase ends with an **acceptance contract**: a written agreement on exactly what "finished" means for that phase, checked by someone other than the person who built it.

### What every contract contains

| Part | What it says |
| --- | --- |
| Entry conditions | Which earlier phases must be accepted before this one can be accepted. Work may start earlier; sign-off may not. |
| Deliverables | The files, code and reports that must exist, with their paths |
| Acceptance criteria | Numbered checks (`AC-<phase>-<nn>`), each with a pass threshold and how it is verified |
| Guarantees to later phases | What later phases may rely on without re-checking |
| Out of scope | What this phase deliberately does not cover, so nobody assumes it does |
| Sign-off | The owner, an independent verifier, and where the evidence lives |
| If rejected | What happens when a criterion fails |

### Rules

1. **All or waived.** A phase is accepted only when every criterion passes or is formally waived.
2. **The verifier is never the owner.** The verifier re-runs the checks themselves; reading the owner's results is not enough.
3. **Evidence is committed.** Each phase has `docs/acceptance/<phase>.md` (template below) with the commit hash, measured values, and links to logs, reports or recordings.
4. **Waivers are explicit.** A waiver needs a written reason, the risk, a plan to close it, and agreement from the owners of every phase that depends on this one.
5. **Rejections are narrow.** A rejection lists the failing criteria. Only those, plus anything they affect, are re-verified.
6. **Guarantees are binding.** If later work breaks a guarantee (for example, a contract version change or a new scoring rule), the phase is reopened and every dependent phase re-runs its affected checks.
7. **Thresholds are fixed before work starts.** Changing one after seeing results needs a waiver, not a quiet edit.
8. **The proof test must pass.** Each phase has one proof test (written just before its contract). A phase whose criteria pass but whose proof test fails is **not** accepted. Proof tests are run by the verifier, on fresh material where the test says so, and their evidence goes in the acceptance record.

### Acceptance record template

Save as `docs/acceptance/<phase>.md`, for example `docs/acceptance/1.2.md`.

```markdown
# Acceptance record: Phase <x.y> <name>

- Commit: <hash>
- Owner: <name>          Verifier: <name>
- Entry conditions met: <yes/no, with links to the accepted records>

| Criterion   | Result (pass / fail / waived) | Measured value | Evidence |
| ----------- | ----------------------------- | -------------- | -------- |
| AC-<x.y>-01 |                               |                |          |

Proof test PT-<x.y>: PASS / FAIL — run by <name> — evidence: <links to recordings, logs, reports>

Waivers: <none, or: reason · risk · plan to close · agreed by>
Decision: ACCEPTED / REJECTED  (<date>)
```

## Test bench: what to install on the laptop

Everything below runs on Windows. Install the **core** group first and add the rest when the phase that needs it starts. The last column says which phase first needs each tool.

### Core (everyone)

| Install | What it's for | First needed |
| --- | --- | --- |
| Git | Source control | 1.1 |
| Python 3.11 with a virtual environment (`venv` or `uv`) | Workshop, twin, evaluation and checker scripts | 1.1 |
| Android Studio (includes the Android SDK, Platform-Tools with `adb`, a JDK, the Profiler and the Database Inspector) | Building the Guard; talking to the phone | 1.1 |
| Flutter SDK | Building and testing the Console, including on-device integration tests | 1.1 |
| scrcpy | Mirrors, controls and records the phone screen from the laptop. This is the main way to capture evidence. | 1.1 |
| ffmpeg | Cutting, downscaling and combining videos; side-by-side comparisons; extracting frames | 2.1 |
| VS Code with Python, Kotlin and Flutter extensions | Day-to-day editing | 1.1 |

### AI and models

| Install | What it's for | First needed |
| --- | --- | --- |
| `torch`, `transformers` or `open_clip_torch`, `ultralytics` (pip) | Running SigLIP2, YOLOE and NudeNet on the laptop | 1.3 |
| `onnx`, `onnxruntime` (pip) | Running the exported model files on the laptop, exactly as the phone will load them | 3.1 |
| Netron | Inspecting exported models visually: shapes and operations | 3.1 |
| `qai-hub` (pip) and a Qualcomm AI Hub account | Compiling, profiling and running models on cloud phones with the same chip | 1.1 |
| `huggingface_hub` (pip) and an account | Downloading models | 1.1 |

### Data and evaluation

| Install | What it's for | First needed |
| --- | --- | --- |
| Label Studio (`pip install label-studio`) | Drawing labels on screenshots and recording keyframes | 1.2 |
| `opencv-python`, `numpy`, `pillow`, `imagehash`, `pandas`, `matplotlib` (pip) | Evaluation, picture hashes, timelines and charts | 1.2 |
| `jsonschema`, `pydantic`, `pytest` (pip) | Contract checks and running checker scripts | 1.1 |

### Phone measurement

Nothing extra to install: these all run through `adb`, except Perfetto's viewer and the optional Battery Historian.

| Tool | What it measures | First needed |
| --- | --- | --- |
| `adb shell dumpsys meminfo <app>` | App memory (PSS) | 3.3 |
| `adb shell dumpsys thermalservice` | The phone's heat status | 3.3 |
| `adb shell dumpsys gfxinfo <app> framestats` | Dropped frames (stutter) in the app being watched | 4.2 |
| Perfetto: viewer at ui.perfetto.dev in Chrome; record with Android Studio's system trace or `adb shell perfetto` | A timeline of every stage of a look; time from content appearing to cover drawn | 4.2 |
| `adb shell dumpsys batterystats` | Battery use per app | 5.3 |
| Battery Historian (optional; runs in Docker Desktop) | Visual battery reports | 5.3 |

### Privacy and server

| Install | What it's for | First needed |
| --- | --- | --- |
| DB Browser for SQLite | Checking the phone's stored data is unreadable without the key | 5.1 |
| PCAPdroid (an app on the phone; no root needed) | Recording all network traffic from the phone, to prove nothing is sent | 6.2 |
| Wireshark | Opening those traffic recordings on the laptop | 6.2 |
| `flask`, `requests` (pip); optionally Docker Desktop | Running the Workshop server and sending it test requests | 6.2 |

### On the phone

- Developer options and USB debugging on; "Stay awake while charging" on during tests.
- Instagram, YouTube, Chrome, WhatsApp, and Netflix (for blind-spot checks), all signed in to **test accounts**, never personal ones.
- PCAPdroid.
- The Veil Test Feed app (below).

### Test fixtures we build ourselves

These are small tools, not product features, but almost every on-device proof test depends on them. Build a first version alongside Phase 1.1 and grow it as phases need more.

1. **Veil Test Feed app.** A tiny app that looks like a social feed but shows content we control: cats, spiders, lookalikes (dogs, foxes), clean posts, Layer 1 test images, abusive comments, a "ruler" pattern, and reposts of the same image. Because we built it, it knows the exact position of every item at every moment, and logs those positions and every tap with timestamps. **This is the ground truth for on-device tests.**
2. **Driver scripts.** Python + `adb` scripts that act like a user: scroll at set speeds and distances, fling, swipe Reels, tap, long-press, rotate, lock and unlock, switch and launch apps. The same script gives the same session every time.
3. **Guard debug log.** In debug builds, the Guard writes every look, finding, track and cover (with timestamps) to a file the laptop can pull. Tests compare it with the Test Feed app's log.
4. **Checker scripts.** These read the Test Feed log and the Guard debug log and produce a pass/fail report: what was on screen, what was covered, how fast, and what was wrongly covered.
5. **Test accounts.** Instagram and YouTube accounts that follow curated content, so tests in real apps see predictable feeds.

**Layer 1 test content:** use only the controlled evaluation images kept in the Workshop, loaded into the Test Feed app for the test and removed afterwards. Never use personal or scraped explicit material on team phones.

---

# Chapter 1: SEE

**The question:** If we take a still screenshot and a list like `["cats"]`, can we find and cover the cats while leaving everything else alone?

**Why first:** It proves the core idea cheaply on a laptop, and its model choices feed chapter 3.

**Chapter gate (target):** On the frozen test screenshots, at least **90% of cats are covered**, and **fewer than 5% of cat-free screenshots** get any wrong cover. Same check for a second concept (spiders) at no worse than 80% / 5%.

**If the gate fails:** Fall back to a fixed-vocabulary detector (80 everyday object classes, which include cat, dog and person) for the demo, plus whole-post matching with the Describer. "Anything you name" becomes a stretch goal.

## Phase 1.1: Foundations

### 1.1.1 Repository and tools

**Goal:** Everyone can build and run every part from a clean checkout.

**Do:**
1. Create the `veil/` repository with the layout above and a top-level `README.md` explaining how to set up each part.
2. Python: pin a version (3.11 suggested), create a virtual environment, add `pytest`, `ruff`, `numpy`, `opencv-python`, `pillow`, `torch`, `onnx`, `onnxruntime`, `open_clip_torch` or `transformers`, `ultralytics`, `pydantic`, `flask`.
3. Android: install Android Studio, create an empty `guard/` app module targeting the phone's Android version; Kotlin + coroutines.
4. Flutter: install the SDK, create an empty `console/` app; confirm it runs on the phone.
5. Add a pre-commit hook for formatting (ruff for Python, ktlint for Kotlin, `dart format` for Flutter).
6. Write `docs/decisions.md` and record decision #1: "hackathon build, licences reviewed before any commercial release" (see Appendix C).

**Produces:** A repository where `pytest`, the Android app and the Flutter app all build and run.

**Done when:** A teammate who did not write it can clone, follow the README, and run all three "hello world" targets on the phone and laptop.

### 1.1.2 Shared contracts, first version

**Goal:** Agree the shapes of data every unit exchanges, before writing units.

**Do:**
1. In `contracts/`, write JSON Schemas for: `Rect`, `Frame` (metadata only), `UiEvent` (scrolled, window changed, content changed, nodes snapshot, screen on/off), `Region`, `Embedding`, `Concept`, `ConceptPack`, `CompiledConcept`, `Finding`, `Track`, `Mask`, `MaskPlan`, `Feedback`, `ModelManifest`, `EngineStats`.
2. Conventions: screen pixels with origin top-left; time in milliseconds on one monotonic clock; fingerprints are normalised and stored as float16; every message carries `contractVersion`.
3. Rule: a fingerprint can only be compared with a concept from the **same model family** (`spaceId`). Write this into the schema description.
4. Generate Python models from the schemas (pydantic). Kotlin and Dart versions come later (chapters 5 and 6), checked against the same schemas.
5. Write 2-3 example JSON files per schema in `contracts/examples/`.
6. Write a test that validates every example against its schema.

**Produces:** `contracts/` folder, generated Python types, example files, a passing validation test.

**Done when:** The validation test passes and all four owners have reviewed and agreed the shapes.

### 1.1.3 Device check and accounts

**Goal:** Know exactly what hardware we target and have every account we need.

**Do:**
1. On the phone: enable Developer options and USB debugging; connect with `adb`.
2. Record the chip: `adb shell getprop ro.soc.model` and `ro.board.platform`. Confirm it is the Snapdragon 8 Elite Gen 5 family. If not, flag it: published speeds in this plan may not apply.
3. Record Android version, OS skin version (OriginOS/Funtouch), RAM, screen resolution and refresh rate in `docs/device-profile.md`.
4. Create a Qualcomm AI Hub account; install `qai-hub` in Python; run `qai-hub configure` with the token; list available cloud devices and note which have the same chip.
5. Create a Hugging Face account and token for model downloads.
6. Check that the phone lets a sideloaded app enable an accessibility service: install any test app, try to enable it, note the "Allow restricted settings" path.

**Produces:** `docs/device-profile.md`, working AI Hub and Hugging Face access.

**Done when:** `qai-hub list-devices` works from the laptop, and the device profile is filled in.

### Proof test: Phase 1.1 · "Fresh-laptop bring-up"

**Proves:** Anyone can get the whole test bench and the phone link working from the written instructions alone.

**Runs on:** A Windows laptop that has never built Veil, plus the iQOO.

**Idea:**
1. A teammate who did not write the README installs the core test bench and clones the repository.
2. They connect the phone and run one "bench check" command.

**It should check:**
- `adb` sees the phone, and scrcpy mirrors it.
- The hello Guard app installs and shows the chip name, Android version and RAM read live from the phone, matching `docs/device-profile.md`.
- The hello Console app installs and launches.
- A tiny model profiling job on Qualcomm AI Hub returns a result.
- Contract validation runs green.
- The first version of the Test Feed app installs and scrolls.

**Passes when:** Every bench-check line is green, with no fixes made outside what the README says.

**Evidence:** Bench-check output and a phone screenshot.

### Acceptance contract: Phase 1.1

**Entry conditions:** None. Needs the phone, a laptop per person, and internet access.

**Deliverables:**
- `veil/` repository with `contracts/`, `workshop/`, `guard/`, `console/`, `data/`, `docs/`, and a setup `README.md`
- `contracts/*.schema.json` for all 16 shared types, examples in `contracts/examples/`, generated Python types
- `docs/device-profile.md` and `docs/decisions.md`
- Working Qualcomm AI Hub and Hugging Face access

**Acceptance criteria:**

| ID | Criterion | Pass threshold | How verified |
| --- | --- | --- | --- |
| AC-1.1-01 | Clean setup | Someone who did not write the README sets up all three parts on a machine that has never built the project | Verifier's own run-through; commands and output saved |
| AC-1.1-02 | Hello apps run | Python tests run; Android and Flutter hello apps launch on the iQOO | Phone screenshots |
| AC-1.1-03 | Contracts complete | All 16 types have a schema with ≥ 2 valid and ≥ 1 invalid example | `pytest contracts/` passes and rejects every invalid example |
| AC-1.1-04 | Contract rules written | Every schema carries `contractVersion`; every fingerprint-bearing type requires `spaceId`; units and coordinate rules are stated in each schema | Schema review checklist |
| AC-1.1-05 | Contracts agreed | All four owners approve contract v1.0 | Names in the acceptance record |
| AC-1.1-06 | Device known | Chip model string, Android build, OS skin, RAM and screen recorded; a chip other than 8 Elite Gen 5 is flagged in `docs/decisions.md` | `adb shell getprop` output saved |
| AC-1.1-07 | Cloud phones reachable | `qai-hub list-devices` lists at least one device of the same chip family | Command output saved |
| AC-1.1-08 | Private data protected | `data/` is ignored by git | `git check-ignore data/x.png` output |

**Guarantees to later phases:**
- Contract v1.0 is frozen. Any change needs a version bump, a note to all owners, and a re-run of every test that uses the changed type.
- The device profile is accurate and can be used for every speed decision.

**Out of scope:** Kotlin and Dart versions of the contracts (built in 5.1 and 6.1).

**Sign-off:** Owner A; contracts approved by A, B, C and D; verifier C. Evidence in `docs/acceptance/1.1.md`.

**If rejected:** Fix the failing items and re-verify only those. Work on other phases may continue, but no other phase can be signed off until 1.1 is accepted, because every phase builds on the repository and contracts.

## Phase 1.2: Test data (ground truth)

### 1.2.1 Collect screenshots

**Goal:** A realistic set of screens to test against.

**Do:**
1. Using team members' own accounts, take about **300 screenshots** across Instagram (feed, Reels, Explore grid, profile grid, DMs), YouTube (home, video playing), Chrome (news site, image search), WhatsApp (chat with images), X/Twitter or Reddit.
2. Aim for: at least **100 with cats** (photos, cartoons, stickers, emoji, small thumbnails, partly visible), **50 with spiders**, and **150 with neither** ("clean").
3. Include hard negatives: dogs, foxes, lions, stuffed toys, cat-shaped logos, the word "cat" in text without a picture.
4. Mix dark mode and light mode, and both portrait and a few landscape.
5. Save each as PNG with a sidecar JSON: `{ "app": "instagram", "surface": "explore", "mode": "dark", "source": "teammate-A" }`.
6. Keep everything in `data/screens/`, which is never pushed to a public remote.

**Produces:** About 300 screenshots plus metadata.

**Done when:** The counts above are met and spot-checked by a second person.

### 1.2.2 Label them

**Goal:** Know exactly where every cat and spider is, so we can score the system.

**Do:**
1. Write `docs/labelling-rules.md`. Suggested rules: label a box around every cat that is at least 30% visible; cartoons, drawings and stickers count; the 🐱 emoji counts as "cat-emoji" (a separate tag, so we can decide later); text that says "cat" is labelled as "cat-text"; mark whether the whole post should be covered (`scope: "WholeElement"`) or just the object.
2. Label with a simple tool (Label Studio or CVAT, run locally).
3. Export to a JSON format matching the `Region`/`Finding` contracts: `{ "image": "s_0042.png", "boxes": [ { "rect": [x, y, w, h], "concept": "cats", "kind": "photo" } ] }`.
4. Have a second person review 20% of labels; fix disagreements and update the rules.

**Produces:** `data/labels/screens.json` and the rules document.

**Done when:** Every screenshot is labelled (including the clean ones, marked as clean), and the review disagreement rate is below about 5%.

### 1.2.3 Split, freeze and score

**Goal:** A fair way to measure progress that cannot be fooled by tuning on the test.

**Do:**
1. Split 60% **dev** (tune freely) and 40% **test** (only for gate reports). Keep app and concept mix similar in both.
2. Record a checksum of the test set in `docs/datasets.md`. The test set never changes after this.
3. Write `workshop/eval/score_screens.py`. Input: predictions in the `Finding` format. Output: per-concept recall (share of labelled items covered), precision (share of covers that were right), and **clean false-cover rate** (share of clean screenshots with any cover).
4. Matching rule: a cover counts as hitting a label if their overlap (IoU) is at least 0.3, or if the cover contains at least 70% of the label (covers are padded on purpose).
5. Test the scorer on a fake "perfect" prediction file and a fake "empty" one.

**Produces:** Frozen splits, the scoring script, `docs/datasets.md`.

**Done when:** The scorer gives 100% for the perfect file and 0% recall for the empty one.

### Proof test: Phase 1.2 · "Blind label audit"

**Proves:** The test data is trustworthy, and the scorer measures what we think it measures.

**Runs on:** Laptop (Label Studio, scorer).

**Idea:**
1. The verifier picks 30 random screenshots and labels them from scratch, without seeing the existing labels.
2. Their labels are compared with the official ones.
3. The verifier hand-makes three prediction files: perfect, empty, and one with deliberate mistakes (2 missed cats, 1 cover on a dog, 1 cover on a clean screenshot), then works out the expected scores by hand.

**It should check:**
- Agreement between the blind labels and the official labels.
- The scorer's numbers for all three files match the hand calculation exactly.
- No screenshot, or near-copy of one, sits in both the dev and test sets.

**Passes when:** AC-1.2-03, AC-1.2-04 and AC-1.2-06 hold on the verifier's own run.

**Evidence:** Comparison output and the hand calculation.

### Acceptance contract: Phase 1.2

**Entry conditions:** Phase 1.1 accepted (the label format schema exists).

**Deliverables:**
- `data/screens/`: about 300 PNG screenshots, each with a metadata JSON
- `data/labels/screens.json` and `docs/labelling-rules.md`
- `docs/datasets.md` with the dev/test split and the test-set checksum
- `workshop/eval/score_screens.py` with unit tests

**Acceptance criteria:**

| ID | Criterion | Pass threshold | How verified |
| --- | --- | --- | --- |
| AC-1.2-01 | Enough material | ≥ 300 screenshots: ≥ 100 with cats, ≥ 50 with spiders, ≥ 150 clean, ≥ 30 hard lookalikes, ≥ 5 apps, ≥ 20% dark mode | Count script output |
| AC-1.2-02 | Everything labelled | 100% of screenshots have a label entry; clean ones are explicitly marked clean; every entry validates against the contract | Validation script |
| AC-1.2-03 | Labels trustworthy | A second person independently re-labels ≥ 20%; disagreement ≤ 5%. A missing box, an extra box, or overlap < 0.5 counts as a disagreement | Comparison script output |
| AC-1.2-04 | Fair split | Dev/test is 60/40 (± 5 points) for each concept and each app; no near-duplicate screenshot appears in both | Split report; picture-hash duplicate check |
| AC-1.2-05 | Test set frozen | Test-set checksum recorded; any change to the test set makes a check fail | Checksum test |
| AC-1.2-06 | Scorer correct | Perfect predictions give recall 1.0, precision 1.0 and clean false-cover 0; empty predictions give recall 0 and false-cover 0; a 5-image hand-worked case matches exactly | Scorer unit tests |
| AC-1.2-07 | Consent and privacy | Every screenshot comes from a team member's own account, with its source recorded; nothing in `data/` is pushed | Metadata check; git check |

**Guarantees to later phases:**
- The test set and the metric definitions are frozen. Changing a scoring rule means re-scoring every earlier report.

**Out of scope:** Moving screens and recordings (Phase 2.1).

**Sign-off:** Owner A, verifier B. Evidence in `docs/acceptance/1.2.md`.

**If rejected:** Collect or label more material until the counts and agreement pass. Tuning in 1.3 may continue on the dev set meanwhile, but no test-set result counts until this phase is accepted.

## Phase 1.3: The SEE prototype

### 1.3.1 Describer and Judge on whole pieces

**Goal:** The simplest version of the idea: cut the screen into pieces, fingerprint them, compare with "cats".

**Do:**
1. Load **SigLIP2-B/16 (224 px)** image and text encoders in Python (float, CPU or laptop GPU).
2. Pieces, version 0: the whole screenshot, plus a grid of overlapping tiles (for example 3 × 6), plus 2-3 crops of any tall element.
3. Write **Teacher v0**: for a concept word, produce:
    - "looks like" prompts: "a photo of a {c}", "a cartoon {c}", "a drawing of a {c}", "a {c} emoji", "a close-up of a {c}";
    - "but not" prompts: hand-written lookalikes for now (cats: dog, fox, lion, stuffed toy);
    - "ignore" prompts shared by all concepts: "a screenshot of an app", "text on a screen", "a user interface".
4. Write **Judge v0**: for each piece, compute similarity to each prompt group, turn the three groups into a probability, and say "hide" when the probability is above a threshold **and** the best "looks like" score beats the best "but not" score by a small margin.
5. Output `Finding` JSON per screenshot and run the scorer on the dev set.
6. Save an image gallery of covers drawn on screenshots (simple HTML page) to eyeball mistakes.

**Produces:** `workshop/twin/teacher.py`, `judge.py`, a baseline score table.

**Done when:** A baseline score exists for cats and spiders on the dev set, and the gallery renders.

### 1.3.2 Add the object finder

**Goal:** Find small things *inside* photos (a cat in the corner of a post), not just whole tiles.

**Do:**
1. Install Ultralytics and load **YOLOE** (start with the small and medium sizes). Verify in its docs which text encoder each YOLOE version uses; YOLOE-26 is reported to use MobileCLIP2-B.
2. Do **not** use the "set classes and bake them in" export. Instead, get the region boxes and the per-region fingerprints *before* the model compares them with text. The user's list must be able to change without rebuilding the model.
3. Compare region fingerprints with concept prompts encoded by YOLOE's **own** text encoder (never mix with SigLIP2 fingerprints).
4. Fuse: for each YOLOE box, also crop it, fingerprint it with SigLIP2, and judge it. Try three variants and score each:
    - A: tiles only (from 1.3.1);
    - B: YOLOE boxes judged by YOLOE's own fingerprints;
    - C: YOLOE boxes judged by SigLIP2 crops, plus tiles for whole-post concepts.
5. Record speed on the laptop per variant (for relative comparison only).

**Produces:** A comparison table of A/B/C on recall, precision, clean false-cover rate.

**Done when:** One variant is clearly best on the dev set, or a reasoned choice is written down.

### 1.3.3 Tune, analyse, decide

**Goal:** Lock the model choice and thresholds, and pass the chapter gate.

**Do:**
1. **Calibrate per concept:** fit a small offset per concept on the dev set so that the same probability means the same confidence for every concept (raw similarity levels differ between concepts).
2. Pick thresholds for the three strictness modes: **Light** (few false covers), **Balanced**, **Strict** (catch nearly everything).
3. Improve the "but not" lists using the gallery: every repeated false cover suggests a lookalike to add.
4. Try example photos: give 3-5 cat photos, average their fingerprints, and use them as an extra signal with its own threshold. Measure the gain.
5. Run once on the **test set** and write `docs/reports/ch1-see.md` with the score table, 10 example successes and 10 failures, and the chosen models.
6. Apply the chapter gate.

**Produces:** Chosen models and thresholds, the chapter report, the go/fallback decision.

**Done when:** The report is written and the gate decision is recorded in `docs/decisions.md`.

### Proof test: Phase 1.3 · "Fresh screenshots"

**Proves:** The idea works on content it has never seen, not just on the test set it was tuned around.

**Runs on:** The iQOO (to take screenshots) and the laptop (to run the prototype).

**Idea:**
1. On the day of the test, take 30 new screenshots from live feeds on the phone: 10 with cats, 5 with spiders, 15 without. Pull them to the laptop with `adb`.
2. Run one command that covers them and builds a gallery.
3. Someone who did not build the prototype reviews the gallery.
4. Repeat with a word never used in tuning (for example "bicycles"), checked the same way.

**It should check:**
- Cats and spiders are covered, including small, cartoon and partly visible ones.
- Nothing else is covered: no dogs, foxes, or text that merely says "cat".
- The new word works with no code or model change.

**Passes when:** The reviewer's tally is in line with AC-1.3-01 to AC-1.3-03, allowing for the small sample, and the new word needed no changes.

**Evidence:** The gallery and the reviewer's tally.

### Acceptance contract: Phase 1.3 (includes the Chapter 1 gate)

**Entry conditions:** Phase 1.2 accepted.

**Deliverables:**
- `workshop/twin/teacher.py`, `judge.py` and the finder integration
- The A/B/C variant comparison table
- `workshop/twin/calibration.json` (per-concept offsets) and the threshold table per mode
- The error gallery (HTML)
- `docs/reports/ch1-see.md` and the decision entry in `docs/decisions.md`

**Acceptance criteria:**

| ID | Criterion | Pass threshold | How verified |
| --- | --- | --- | --- |
| AC-1.3-01 | Cats caught | Balanced recall on the test set ≥ 90% | Scorer on the test set |
| AC-1.3-02 | Few wrong covers | ≤ 5% of clean test screenshots get any wrong cover (Balanced) | Scorer on the test set |
| AC-1.3-03 | Second concept | Spiders: recall ≥ 80%, clean false-cover ≤ 5% | Scorer on the test set |
| AC-1.3-04 | Modes behave | On dev: recall Light ≤ Balanced ≤ Strict, and wrong covers Light ≤ Balanced ≤ Strict | Score table |
| AC-1.3-05 | List changes need no rebuild | Switching the list from cats to spiders to a new word needs no model change or re-export | Demonstration recorded in the report |
| AC-1.3-06 | Unseen concept works | A word never used in tuning (for example "snakes") produces a valid concept card and runs end to end; its score is reported (no threshold) | Report section |
| AC-1.3-07 | Reproducible | One command regenerates every number in the report from a clean checkout, within ± 0.5 points | Verifier re-runs it |
| AC-1.3-08 | Test set not overused | The test set has been scored at most 3 times in total, each run logged | Run log |
| AC-1.3-09 | Choices documented | Models, versions, `spaceId`s, licences, thresholds and calibration recorded | Decision record |

**Guarantees to later phases:**
- The chosen model names and versions are final for Chapter 3, unless Chapter 3's gate forces a change.
- The Judge maths and concept card format (v1) are what Chapters 2 and 5 implement.
- The threshold tables per mode are the starting values for Chapter 2.

**Out of scope:** Moving screens, speed on the phone, the phone itself.

**Sign-off:** Owner A; verifiers B (re-runs the numbers) and D (reviews the gallery from a user's point of view). Evidence in `docs/acceptance/1.3.md`.

**If rejected:** Apply the Chapter 1 fallback (fixed 80-class detector plus whole-post matching), record it in `docs/decisions.md`, and accept the phase against the fallback's own thresholds: cats ≥ 85%, clean false-cover ≤ 5%.

---

# Chapter 2: MOTION

**The question:** On real moving screens (scrolling feeds, Reels, videos), does the system look only when needed, cover things fast, and keep covers steady without flicker?

**Depends on:** Chapter 1 (the Judge and Describer). Uses the event logger from 4.2.1 when it is ready; until then, scroll is estimated from the video.

**Chapter gate (target):** On the frozen test recordings, in Balanced mode:
- every concept appearance is covered within **0.3 s** of becoming visible (95% of appearances);
- **zero flicker events** (a cover disappearing and reappearing on the same item within 1 s);
- fewer than **one wrong cover per minute** on clean recordings;
- the system analyses fewer than **15% of frames**.

**If the gate fails:** Use solid covers only, hold covers longer after the last sighting, and raise looks per second (trading battery for safety).

## Phase 2.1: Recordings and replay

### 2.1.1 Record sessions

**Goal:** Realistic moving test material with matching scroll information.

**Do:**
1. Record **10-15 minutes** of screen video on the phone (`adb shell screenrecord` or the built-in recorder): Instagram feed scrolling, Reels swiping, Explore grid, YouTube with a cat video, a film clip with a scene cut, a news site.
2. Include slow scrolls, fast flings, pauses, app switches, and a screen lock/unlock.
3. While recording, log scroll and window events (use the logger from 4.2.1 if ready). Save as JSONL with the same clock as the video.
4. If the logger isn't ready: write a quick estimator that compares neighbouring frames row by row to guess vertical scroll, and mark these sessions "estimated scroll".
5. Downscale copies to 360 × 800 (the Guard's working size) and keep originals.

**Produces:** `data/recordings/*.mp4` plus matching `*.events.jsonl`.

**Done when:** At least 6 sessions exist with event logs or estimated scroll, covering every listed situation.

### 2.1.2 Label recordings

**Goal:** Know when and where each concept is visible over time.

**Do:**
1. For each session, mark time spans where each concept is visible (start and end time).
2. Every 0.5 s within those spans, draw boxes (keyframes); boxes in between are interpolated.
3. Mark scene cuts and app switches.
4. Mark "clean" stretches (no concept visible) explicitly.
5. Split sessions: two-thirds dev, one-third test; freeze the test sessions with a checksum.

**Produces:** `data/labels/recordings/*.json`.

**Done when:** All sessions are labelled and a second person has reviewed one full session.

### 2.1.3 Replay harness

**Goal:** Feed recordings into the twin exactly as the phone would, and get a covered video out.

**Do:**
1. Write a player that reads a video and its event log, advances a **virtual clock**, and hands each frame and event to the pipeline in time order.
2. Make it run in two speeds: real time (to watch) and as fast as possible (to evaluate).
3. Write a **cover renderer** that paints the pipeline's `MaskPlan` onto the frames and writes an MP4, so humans can watch the result.
4. Add a "self-capture" option: paint the previous covers into the *next* input frame, to reproduce what the phone will see (our own covers in our own capture).
5. Define the **tape format**: JSONL inputs (thumbnails, events, findings, fingerprints) and JSONL expected outputs (scheduler decisions, tracks, mask plans). Add a recorder that writes tapes during replay.

**Produces:** `workshop/replay/`, covered output videos, a tape writer.

**Done when:** A recording replays end to end with a dummy pipeline and produces a watchable covered video and a tape.

### Proof test: Phase 2.1 · "Known scroll replay"

**Proves:** A replay on the laptop is faithful to what really happened on the phone.

**Runs on:** The iQOO (Test Feed app, driver script) and the laptop (replay harness).

**Idea:**
1. Record a 1-minute session in the Test Feed app while a driver script performs scrolls of known distances at known times.
2. Replay it in the harness with an on-screen marker drawn at every logged scroll event.
3. Replay it two more times.

**It should check:**
- Markers line up with the visible movement (within 1 frame).
- Replayed scroll distances match what the driver script did.
- All three replays produce identical tapes.
- With self-capture switched on, covers from one frame appear in the next.

**Passes when:** AC-2.1-03, AC-2.1-05 and AC-2.1-07 hold on this fresh session.

**Evidence:** The marked replay video and the tape hashes.

### Acceptance contract: Phase 2.1

**Entry conditions:** Phase 1.1 accepted. Event logs from 4.2.1 are preferred; estimated scroll is accepted for at most half of the sessions.

**Deliverables:**
- `data/recordings/`: at least 6 sessions, each with an event log (`*.events.jsonl`) and downscaled copies
- `data/labels/recordings/*.json`
- `workshop/replay/`: player with a virtual clock, cover renderer, self-capture option
- `contracts/tape.schema.json` and the tape writer

**Acceptance criteria:**

| ID | Criterion | Pass threshold | How verified |
| --- | --- | --- | --- |
| AC-2.1-01 | Enough material | ≥ 10 minutes total; every listed situation (slow scroll, fling, Reels swipe, Explore grid, video with a scene cut, app switch, lock/unlock) appears at least twice | Session index |
| AC-2.1-02 | Real scroll data | ≥ 3 sessions have logged (not estimated) scroll events | Session index |
| AC-2.1-03 | In sync | On 10 sampled scrolls per session, the logged time is within ± 1 frame (33 ms) of the visible movement | Spot-check sheet |
| AC-2.1-04 | Labelled and frozen | 100% of sessions labelled; review disagreement ≤ 5%; test sessions frozen with a checksum | Review output; checksum test |
| AC-2.1-05 | Replay is deterministic | Replaying the same session twice at full speed gives byte-identical tapes | Hash comparison |
| AC-2.1-06 | Real-time capable | Real-time mode keeps pace with the video using a dummy pipeline | Timing log |
| AC-2.1-07 | Self-capture simulated | With the option on, frame N+1 contains the covers from plan N, positioned within 1 px | Unit test |
| AC-2.1-08 | Tapes valid | Every tape line validates against the tape schema | Validation script |

**Guarantees to later phases:**
- Tape format v1 is fixed; the Kotlin port (5.1) consumes it unchanged.
- Virtual clock rule: events stamped at time t are delivered before the frame stamped at t.

**Out of scope:** Any decision logic; this phase only provides material and tooling.

**Sign-off:** Owner B, verifier A. Evidence in `docs/acceptance/2.1.md`.

**If rejected:** Record more sessions (re-record with the 4.2.1 logger if scroll sync fails). Phase 2.2 work may continue on dev sessions.

## Phase 2.2: Deciding when to look (the Gatekeeper)

### 2.2.1 Change detector

**Goal:** Cheaply tell how much the screen changed since the last look.

**Do:**
1. Shrink each frame to a **32 × 64 grayscale** thumbnail; split into 32 tiles of 8 × 8.
2. Compare each tile with the **last analysed** thumbnail, not the previous frame, so slow changes still add up and dropped frames lose nothing.
3. Before comparing, shift the reference by the scroll distance from events, so a pure scroll only lights up the newly revealed strip.
4. Flag a **scene cut** when most tiles changed a lot (starting point: 60% of tiles with a large global change).
5. Ignore the status bar and navigation bar rows.
6. Use whole-number maths only, so the phone version can match exactly.
7. Unit tests with synthetic frames: static, small blink, pure scroll, scene cut, slow fade.

**Produces:** `workshop/twin/change.py` + tests.

**Done when:** All synthetic cases give the expected result, and on recordings scene cuts match the labelled cuts at least 90% of the time.

### 2.2.2 Burst scheduler

**Goal:** Decide when to run a look and what part of the screen to look at.

**Do:**
1. Write it as a pure function: `(state, inputs) → (new state, look request or nothing)`. Time comes in as an input; no clocks inside.
2. States: **Idle** (screen off or skipped app), **Watching** (normal rate), **Hot** (something almost matched: look more often for a few seconds), **Throttled** (phone hot or battery saver: look half as often or less).
3. Immediate looks, in priority order: scene cut, app/window change, swipe, newly revealed strip.
4. Periodic looks at the mode's base rate: Light 1 per second, Balanced 3, Strict 8 (starting values).
5. **Never queue:** if a look is still running, skip; the change stays pending for the next tick.
6. Regular full-screen check-ups (every 10 / 5 / 2 s by mode).
7. Unit tests for each transition.

**Produces:** `workshop/twin/scheduler.py` + tests.

**Done when:** All transition tests pass and a replay shows sensible look timing on every recording type.

### 2.2.3 Measure the look budget

**Goal:** Prove the Gatekeeper saves work without missing things.

**Do:**
1. Replay all dev recordings in each mode and record: looks per minute, share of frames analysed, time from new content appearing to the first look.
2. Break it down by situation: feed scroll, Reels, video, static reading.
3. Tune thresholds (tile change level, minimum gap between immediate looks, Hot duration).
4. Plot looks per minute vs time-to-first-look per mode, and pick the defaults.

**Produces:** A tuning report section and updated default parameters.

**Done when:** Balanced mode analyses under 15% of frames while 95% of new content gets a look within 0.2 s.

### Proof test: Phase 2.2 · "Look timeline"

**Proves:** The Gatekeeper looks when it should and rests when it should.

**Runs on:** The laptop, using a fresh recording from the phone.

**Idea:**
1. Record a fresh 3-minute session that mixes 30 s doing nothing, a slow scroll, a fast fling, Reels swipes, a video with scene cuts, and an app switch.
2. Replay it through the Gatekeeper and draw a timeline: how much the screen changed, the scroll events, and every look with its reason.
3. Replay again with every look artificially slowed to 0.5 s.

**It should check:**
- No looks during the idle 30 s, apart from the scheduled check-ups.
- A look at every swipe, scene cut and app switch.
- During video, looks stay within the mode's cap.
- With slowed looks, nothing piles up and skipped frames are counted.

**Passes when:** A reviewer finds no missed trigger and no idle-time looks beyond the check-ups, and AC-2.2-04 to AC-2.2-06 hold.

**Evidence:** The timeline chart and the reviewer's notes.

### Acceptance contract: Phase 2.2

**Entry conditions:** Phases 2.1 and 1.3 accepted.

**Deliverables:**
- `workshop/twin/change.py` and `scheduler.py` with unit and property tests
- `workshop/twin/params.json`: the tuned parameter table per mode
- The look-budget section of the Chapter 2 report

**Acceptance criteria:**

| ID | Criterion | Pass threshold | How verified |
| --- | --- | --- | --- |
| AC-2.2-01 | Synthetic cases | Static: no change. Blink: below threshold. Pure scroll: only the revealed strip. Scene cut: flagged. Slow fade: triggers before the fade ends | Unit tests |
| AC-2.2-02 | Scene cuts found | ≥ 90% of labelled cuts detected; ≤ 1 false cut per minute | Eval on dev recordings |
| AC-2.2-03 | Pure and repeatable | 1,000 random input sequences run twice give identical outputs; the code has no wall clock or randomness | Property test; code review |
| AC-2.2-04 | Never queues | With looks forced to take 500 ms, the pending queue is always empty and skipped frames are counted | Stress test |
| AC-2.2-05 | Light on effort | Balanced analyses < 15% of frames on dev recordings | Eval |
| AC-2.2-06 | Quick to notice | 95% of new content gets a look within 0.2 s of video time (Balanced) | Eval |
| AC-2.2-07 | Heat respected | In Throttled, looks per second ≤ 50% of the Watching rate | Unit test |
| AC-2.2-08 | Whole numbers only | The change detector uses integer maths only | Code review checklist |

**Guarantees to later phases:**
- The meaning of a look request (why, where, deadline) is fixed.
- The parameter table per mode (v1) is what the phone uses until retuned through the twin.

**Out of scope:** Covers, tracking, the phone.

**Sign-off:** Owner B, verifier A. Evidence in `docs/acceptance/2.2.md`.

**If rejected:** Retune on dev recordings. If AC-2.2-05 and AC-2.2-06 cannot both pass, prefer AC-2.2-06 (safety over battery) and record a waiver on AC-2.2-05 for Chapter 5 to absorb.

## Phase 2.3: Steady covers (the Follower and Painter)

### 2.3.1 Tracker

**Goal:** Turn individual sightings into stable covers that follow their item.

**Do:**
1. Match new findings to existing covers by overlap, in two passes: confident findings first (overlap at least 0.3), then near-threshold findings, which only keep existing covers alive (overlap at least 0.5).
2. On every scroll event, **shift all covers** by the scroll distance, with no AI.
3. A new cover becomes "confirmed" after 3 / 2 / 1 sightings (Light / Balanced / Strict). Layer 1 always confirms on the first sighting.
4. Keep a cover for a short hold after its last sighting (0.8 / 1.5 / 3 s).
5. **Self-capture rule:** if our own cover hides at least 80% of an item, a missing sighting does not count against it. It stays covered until the item scrolls away, the app changes, the user peeks, or a maximum hold (10 / 20 / 30 s) passes.
6. **Parked covers:** an item scrolled just off screen keeps a virtual position for 3 s; if it scrolls back, the cover reappears immediately and is re-checked.
7. Whole-number geometry and fixed tie-breaking so the phone version can match exactly.

**Produces:** `workshop/twin/tracker.py` + tests.

**Done when:** With self-capture switched on in the replay, no recording shows flicker.

### 2.3.2 Mask planner and memory

**Goal:** Turn tracks into clean covers, and avoid re-fingerprinting things already seen.

**Do:**
1. **Mask planner:** draw confirmed covers only; pad each by 4 / 6 / 10% of its short side; drop tiny ones in Light; merge overlapping covers; whole-post covers for text and abstract concepts (using the post's bounds when available); at most 24 covers.
2. Cover styles: Layer 1 always solid; Layer 2 blur (Light, Balanced) or solid (Strict); optional label "Hidden · cats".
3. **Memory (cache):** a 64-bit picture hash of each crop; reuse the stored fingerprint when a near-identical crop was seen recently (up to about 8,000 entries, kept in memory only, cleared on screen lock).
4. Store fingerprints, not verdicts, so a change to the user's list applies instantly.
5. Measure cache hit rate per situation (feed scroll back and forth, Reels, video).

**Produces:** `workshop/twin/planner.py`, `cache.py`, hit-rate numbers.

**Done when:** Covers look clean in output videos, and cache hits are reported per situation.

### 2.3.3 Motion evaluation and golden tapes

**Goal:** Pass the chapter gate and freeze the reference behaviour for the phone port.

**Do:**
1. Write `workshop/eval/score_motion.py`, which reports per mode:
    - seconds-to-cover (median and 95th percentile);
    - share of concept-visible time that was covered;
    - flicker events per minute;
    - wrong-cover seconds per minute on clean stretches;
    - share of frames analysed.
2. Run on the test recordings and write `docs/reports/ch2-motion.md` with numbers and 3 short covered videos.
3. Record **golden tapes** from 3-4 representative sessions: inputs plus expected outputs for the change detector, scheduler, tracker and planner.
4. Apply the chapter gate.

**Produces:** The motion report, golden tapes in `contracts/tapes/`, the gate decision.

**Done when:** The gate decision is recorded and the tapes are committed.

### Proof test: Phase 2.3 · "Watch it like a user"

**Proves:** The covers look right to a human, not just to the scorer.

**Runs on:** The laptop (replay), on test recordings plus one fresh "torture" recording, all with self-capture switched on.

**Idea:**
1. Produce side-by-side videos (original next to covered) for every test session.
2. A reviewer who did not build the Follower watches them at normal speed and marks every late cover, flicker, cover that slides off its item, and wrong cover.
3. Record a fresh torture session: fling back and forth over a cat 10 times, swipe Reels fast, and cut from a scene onto a cat.

**It should check:**
- No flicker anywhere.
- Covers usually appear before the reviewer can make out the cat.
- Covers stay glued during fast flings.
- A cat scrolled away and back is covered again immediately.

**Passes when:** The reviewer's marks agree with the motion scorer, and AC-2.3-01 to AC-2.3-05 hold.

**Evidence:** The side-by-side videos and the reviewer's marked list.

### Acceptance contract: Phase 2.3 (includes the Chapter 2 gate)

**Entry conditions:** Phase 2.2 accepted.

**Deliverables:**
- `workshop/twin/tracker.py`, `planner.py`, `cache.py` with tests
- `workshop/eval/score_motion.py`
- `docs/reports/ch2-motion.md` with 3 covered example videos
- Golden tapes in `contracts/tapes/`

**Acceptance criteria:**

| ID | Criterion | Pass threshold | How verified |
| --- | --- | --- | --- |
| AC-2.3-01 | Fast covers | Time to cover, p95 ≤ 0.3 s (Balanced, test recordings) | Motion scorer |
| AC-2.3-02 | No flicker | 0 flicker events in every test session with self-capture on | Motion scorer |
| AC-2.3-03 | Few wrong covers | ≤ 1 wrong cover per minute on clean stretches | Motion scorer |
| AC-2.3-04 | Coverage | ≥ 95% of the time a concept is visible, it is covered | Motion scorer |
| AC-2.3-05 | Glued while scrolling | Median gap between cover and labelled box ≤ 8 px during scrolls | Motion scorer |
| AC-2.3-06 | Layer 1 rules | Layer 1 covers are solid, appear on first sighting, and cannot be peeked | Unit tests |
| AC-2.3-07 | Memory is safe | On 1,000 different crops, wrong reuse < 0.1%; hit rate reported per situation | Cache test; report |
| AC-2.3-08 | Golden tapes | ≥ 3 tapes (feed scroll, Reels, video); each validates and replays to identical outputs twice | Tape tests |

**Guarantees to later phases:**
- The golden tapes are frozen. The phone version (5.1) must reproduce them exactly.
- The motion metric definitions are frozen and reused in Chapter 5 and the final report.

**Out of scope:** Real phone timing, AI chip speed.

**Sign-off:** Owner B; verifiers A (re-runs the scores) and D (watches the covered videos for anything a user would notice). Evidence in `docs/acceptance/2.3.md`.

**If rejected:** Apply the Chapter 2 fallback (solid covers, longer holds, more looks per second), re-score, and record the battery impact for Chapter 5.

---

# Chapter 3: SPEED

**The question:** Do the chosen models run fast enough, and accurately enough, on the phone's AI chip?

**Depends on:** Chapter 1's model choice (1.3.3). Sub-phase 3.3.1 can start immediately with any public model.

**Known starting numbers (published, Snapdragon 8 Elite Gen 5, Qualcomm AI Hub):** SigLIP2-B/16 image encoder 2.1 ms (w8a16), text encoder 1.2 ms; YOLOv8n detector 0.59 ms (w8a8).

**Chapter gate (target):**
- every model runs fully on the AI chip (no parts silently falling back to the main processor);
- one full Balanced look takes **under 45 ms** at the 95th percentile on the real phone;
- all models together stay **under 3 GB** of memory;
- quantised accuracy stays within **2 points** of the chapter 1 test scores.

**If the gate fails:** Switch the runtime to LiteRT. If the object finder still fails, drop it and use the UI layout plus tiles (whole-post covers only), or switch to the fixed 80-class detector.

## Phase 3.1: Export the models

### 3.1.1 Describer (SigLIP2) export

**Goal:** Phone-ready image and text encoders that match the laptop version.

**Do:**
1. Download Qualcomm AI Hub's ready-made SigLIP2 exports (float and w8a16 ONNX), or export from the Hugging Face model with fixed input shapes.
2. Also export batch sizes 4 and 16 for the image encoder (for grids of thumbnails).
3. Parity check: on 200 crops from the chapter 1 dev set, the cosine similarity between laptop-float and exported fingerprints must be at least 0.98.
4. Check the text encoder with its own tokenizer against the reference on 100 prompts (cosine at least 0.999 in float).

**Produces:** `workshop/forge/siglip2/` with ONNX files and a parity report.

**Done when:** Both parity checks pass.

### 3.1.2 Object finder (YOLOE) export

**Goal:** A phone-ready finder that outputs boxes plus fingerprints, not baked-in classes.

**Do:**
1. Write a small wrapper around the chosen YOLOE model that stops **before** the text comparison and outputs: top 100 boxes, an "objectness" score, and a normalised 512-number fingerprint per box (plus mask coefficients if using segmentation).
2. Fix the input shape (640 × 640) and export to ONNX (opset 17-20).
3. If the AI chip can't run a step (for example "top-K" selection), move that step out of the model and do it in app code.
4. Parity check against Ultralytics' own predictions with the same prompts: box overlap above 0.95 and score difference below 0.02.
5. Export the matching text encoder (the one YOLOE was trained with) and check parity.

**Produces:** `workshop/forge/yoloe/` with the wrapper, ONNX files and a parity report.

**Done when:** Parity passes and the export has a fixed shape.

### 3.1.3 Layer 1 and text models export

**Goal:** Phone-ready safety models.

**Do:**
1. NudeNet 320n (always-on, small) and 640m (Balanced and Strict): export with fixed shapes; do box decoding and overlap removal in app code.
2. Parity: at least 98% of detections match the float model on 200 images from a safe, licensed evaluation set (keep the set in the Workshop only).
3. Toxicity text model (multilingual small model): export with sequence lengths 128 and 256; parity of scores (AUC drop under 0.005 on a public toxicity sample).
4. OCR: plan to use Google ML Kit text recognition on the phone for now (no export needed). Note PaddleOCR mobile as a later NPU option.

**Produces:** `workshop/forge/nudenet/`, `forge/toxicity/`, parity reports.

**Done when:** All parity checks pass.

### Proof test: Phase 3.1 · "Same answers, new engine"

**Proves:** The exported models behave like the originals inside the real pipeline, not just number by number.

**Runs on:** The laptop, with ONNX Runtime loading the exported files.

**Idea:**
1. Re-run the Phase 1.3 "Fresh screenshots" test with the exported model files instead of the originals.
2. Change the concept list three times without touching the model files.
3. Open each exported file in Netron.

**It should check:**
- The covered galleries are practically identical to the originals (at least 98% of decisions the same).
- List changes work with the same model files.
- No model has a variable input or output size.

**Passes when:** AC-3.1-02 to AC-3.1-04 hold.

**Evidence:** Both galleries, a decision-difference report, and Netron screenshots.

### Acceptance contract: Phase 3.1

**Entry conditions:** Phase 1.3 accepted (the model choice).

**Deliverables:**
- `workshop/forge/<model>/` for each model: export script, ONNX files, parity report
- SigLIP2 image (batch 1, 4, 16) and text; YOLOE wrapper and its text encoder; NudeNet 320n and 640m; toxicity model (lengths 128 and 256)
- A checksum list of every exported file

**Acceptance criteria:**

| ID | Criterion | Pass threshold | How verified |
| --- | --- | --- | --- |
| AC-3.1-01 | Fixed shapes | No model has a variable-size input or output | Shape-check script |
| AC-3.1-02 | Describer matches | Image fingerprints vs laptop float on 200 crops: mean cosine ≥ 0.98 and worst 5% ≥ 0.95. Text: ≥ 0.999 on 100 prompts | Parity report |
| AC-3.1-03 | Finder matches | Box overlap > 0.95 and score difference < 0.02 vs Ultralytics; every fingerprint has length 1 ± 0.001 | Parity report |
| AC-3.1-04 | List not baked in | The same exported finder file works with two different concept lists | Demonstration in the report |
| AC-3.1-05 | Safety and text match | NudeNet ≥ 98% detection agreement; toxicity AUC drop ≤ 0.005 | Parity report |
| AC-3.1-06 | Reproducible | Re-running each export script gives the same checksum, or any non-determinism is documented and parity still passes | Verifier re-runs the scripts |
| AC-3.1-07 | Licences recorded | Licence and source URL recorded for every file | Draft manifests |

**Guarantees to later phases:** Exported files with fixed input and output specs, ready to profile.

**Out of scope:** Speed and memory (3.2, 3.3).

**Sign-off:** Owner A, verifier B. Evidence in `docs/acceptance/3.1.md`.

**If rejected:** If the finder cannot export without baking in classes, or fails parity, switch to UI-layout pieces plus tiles for Layer 2 and record the change. Chapter 1's scores must be re-run for the new piece source.

## Phase 3.2: Profile on cloud phones

### 3.2.1 Compile and profile

**Goal:** Real chip numbers before touching the phone.

**Do:**
1. For every exported model, submit compile and profile jobs to Qualcomm AI Hub on the closest available device (same chip family).
2. Record per model: latency, peak memory, and **share of layers on the AI chip**.
3. For any layer running off the AI chip, find the cause (unsupported operation, dynamic shape) and fix the export.
4. Note that cloud devices may be slightly faster than the actual phone; treat their numbers as best case.

**Produces:** `docs/reports/ch3-profile.md` with a table per model.

**Done when:** Every model shows 100% of layers on the AI chip, or the remaining exceptions are documented with a plan.

### 3.2.2 Choose precision per model

**Goal:** Smallest and fastest settings that keep accuracy.

**Do:**
1. For each model, compare float16 vs w8a16 (and w8a8 for the simple detectors).
2. Re-run the chapter 1 test-set scoring using the quantised models' outputs (from AI Hub inference jobs or the phone).
3. Pick the fastest setting that stays within 2 points of the float scores. Avoid mixed int16 settings that are known to be slower for transformer models.

**Produces:** A precision decision per model in the report.

**Done when:** Each model has a chosen precision with before/after scores.

### 3.2.3 Batch variants, budget and manifests

**Goal:** A per-look time budget and the files the phone will load.

**Do:**
1. Profile Describer batch sizes 1, 4 and 16. Link them into one shared-weight package if the toolchain allows it.
2. Fill the budget table for one Balanced look: preprocessing, NudeNet, YOLOE, Describer on new crops, toxicity on new text, and the logic steps.
3. Decide model sizes per mode (for example YOLOE small in Light, medium in Balanced, large in Strict).
4. Write one **ModelManifest** JSON per model: name, version, task, input and output shapes, preprocessing, `spaceId`, paired text encoder, precision, runtime, file checksum, source URL, licence.

**Produces:** The budget table, `workshop/forge/manifests/*.json`.

**Done when:** The budget adds up to under 45 ms (estimate) for Balanced, and every manifest validates against the schema.

### Proof test: Phase 3.2 · "Cloud phone run"

**Proves:** The models run on the real chip type, with real inputs, and give the same answers.

**Runs on:** Qualcomm AI Hub cloud phones of the same chip family.

**Idea:**
1. Send each model, with 50 real crops and prompts from the test set, as an inference job.
2. Pull the outputs back and compare them with the laptop's outputs.
3. Open the layer placement report for each model.

**It should check:**
- Outputs match the laptop (cosine 0.98 or higher).
- 100% of layers run on the AI chip.
- Measured times match the budget table.

**Passes when:** AC-3.2-01 to AC-3.2-03 hold.

**Evidence:** AI Hub job links and the comparison report.

### Acceptance contract: Phase 3.2

**Entry conditions:** Phase 3.1 accepted.

**Deliverables:**
- `docs/reports/ch3-profile.md`: per-model table with links to every Qualcomm AI Hub job
- The precision decision per model, with before/after scores
- The per-look budget table
- `workshop/forge/manifests/*.json`

**Acceptance criteria:**

| ID | Criterion | Pass threshold | How verified |
| --- | --- | --- | --- |
| AC-3.2-01 | All on the AI chip | 100% of layers on the AI chip for every model used during looks; at most one documented exception, outside the look path | AI Hub profile results |
| AC-3.2-02 | Accuracy kept | Chosen precision stays within 2 points of float on the Chapter 1 test scores | Scorer |
| AC-3.2-03 | Budget fits | Profiled total for one Balanced look ≤ 45 ms | Budget table |
| AC-3.2-04 | Manifests valid | Every manifest validates; checksums match the files; `spaceId` and paired text encoder set for every fingerprint model | Validation script |
| AC-3.2-05 | Auditable | Every number in the report links to its AI Hub job | Report review |

**Guarantees to later phases:** The manifests (v1) are the only way the phone learns about models. Precision and batch sizes are fixed for Phase 3.3.

**Out of scope:** The real phone (3.3); cloud numbers are treated as best case.

**Sign-off:** Owner A, verifier C. Evidence in `docs/acceptance/3.2.md`.

**If rejected:** Rework exports for layers off the AI chip; drop to smaller model sizes if the budget does not fit.

## Phase 3.3: Runtime on the real phone

### 3.3.1 Runtime smoke test

**Goal:** Prove the phone can run a model on its AI chip through our chosen runtime.

**Do:**
1. Create a tiny Android test app using ONNX Runtime with Qualcomm's QNN provider.
2. Apply the known setup fixes for this chip generation (native library declaration, library path, legacy packaging, matching runtime version); see Appendix D.
3. **Turn off silent fallback** to the main processor, so a failure is loud.
4. Load a public ViT or the SigLIP2 image encoder and run 100 inferences; confirm in the profile that the QNN provider ran it.
5. In parallel, run the same model through LiteRT with its NPU accelerator.

**Produces:** `guard/smoketest/` app, a timing log for both runtimes.

**Done when:** The model runs on the AI chip in under 10 ms with no fallback, in at least one runtime.

### 3.3.2 All models resident

**Goal:** Everything loaded at once, warm, and measured properly.

**Do:**
1. Load all chosen models at start, run 2 warm-up passes each, and keep them in memory.
2. Cache the compiled versions on disk so a restart doesn't recompile.
3. Measure over 1,000 runs per model: typical (p50) and worst-normal (p95) time, plus first-run-after-idle time.
4. Measure total app memory (PSS) with everything loaded.
5. Use "burst" performance mode during a look and low-power mode between looks; measure the difference.
6. Run all AI calls one after another on a single worker (the chip runs them in sequence anyway).

**Produces:** A timing and memory table from the real phone.

**Done when:** Memory is under 3 GB and every model's p95 is recorded.

### 3.3.3 Soak test and runtime decision

**Goal:** Confirm it holds up over time, then choose the runtime.

**Do:**
1. Run a 10-minute loop at 3 looks per second using real recorded frames, with screen capture active.
2. Record p95 look time, errors, memory over time, phone temperature and throttling.
3. Compare ONNX Runtime and LiteRT on speed, stability and effort.
4. Write `docs/reports/ch3-speed.md` and record the runtime decision.
5. Apply the chapter gate.

**Produces:** The speed report and the gate decision.

**Done when:** The decision is recorded and the runtime wrapper is ready to reuse in chapter 5.

### Proof test: Phase 3.3 · "AI in your hand"

**Proves:** The iQOO itself runs the AI fast, steadily and correctly.

**Runs on:** The iQOO.

**Idea:**
1. A test app on the phone runs a full look (without screen capture yet) over 50 screenshots stored on the phone, and shows the covers and timings on screen.
2. It then loops for 10 minutes at 3 looks per second while someone holds the phone normally.
3. Finally, close and reopen the app and time how long until it is ready.

**It should check:**
- Covers match the laptop's covers for the same screenshots.
- p95 look time is within the budget.
- No errors and no memory creep during the 10 minutes.
- The phone stays comfortable to hold, with thermal status logged throughout.
- The app is ready again quickly after reopening.

**Passes when:** AC-3.3-01 to AC-3.3-06 hold.

**Evidence:** On-phone screen recording (scrcpy), timing, memory and thermal logs.

### Acceptance contract: Phase 3.3 (includes the Chapter 3 gate)

**Entry conditions:** Phase 3.2 accepted. The 3.3.1 smoke test may run and pass earlier, but the phase is signed off only after 3.2.

**Deliverables:**
- `guard/smoketest/` test app
- The runtime wrapper used by the Guard (load, run, release)
- Timing and memory tables from the real phone
- The 10-minute soak log
- `docs/reports/ch3-speed.md` and the runtime decision in `docs/decisions.md`

**Acceptance criteria:**

| ID | Criterion | Pass threshold | How verified |
| --- | --- | --- | --- |
| AC-3.3-01 | No silent fallback | Fallback to the main processor is disabled, and every model still loads and runs on the AI chip | Runtime logs |
| AC-3.3-02 | Fast look | One full Balanced look, p95 ≤ 45 ms on the phone with real frames | Timing table |
| AC-3.3-03 | Memory | With all models loaded, app memory (PSS) ≤ 3 GB | `dumpsys meminfo` |
| AC-3.3-04 | Stable | 10-minute soak at 3 looks/s: 0 errors; memory growth ≤ 5% after warm-up; last-minute p95 within 20% of first-minute p95 | Soak log |
| AC-3.3-05 | Quick start | All models ready ≤ 5 s after a restart, with the compiled cache present | Timing log |
| AC-3.3-06 | Phone matches laptop | Phone vs laptop-float fingerprints: cosine ≥ 0.98 | Parity test |
| AC-3.3-07 | Decision made | ONNX Runtime vs LiteRT comparison and the choice recorded | Decision record |

**Guarantees to later phases:**
- The runtime wrapper's interface (load, run, release) stays fixed for Chapter 5.
- Per-model latencies on the real phone are known and can be used for scheduling.

**Out of scope:** Screen capture, the live pipeline, battery.

**Sign-off:** Owner A, verifier C (runs it on the phone independently). Evidence in `docs/acceptance/3.3.md`.

**If rejected:** Apply the Chapter 3 fallback: switch to LiteRT, then smaller models, then drop the object finder. Re-run all criteria after each step.

---

# Chapter 4: PLUMBING

**The question:** Can the phone watch its own screen in small frames, know when and how far things scroll, and draw covers on top of any app, with no AI involved yet?

**Depends on:** Nothing. Can start immediately.

**Chapter gate (target):**
- frames arrive at 360 × 800 only when the screen changes;
- a test box stays glued to an item during 30 s of scrolling, with drift under 8 pixels;
- permissions survive the realistic flows on the iQOO (lock/unlock handled);
- we know for certain whether our own covers appear in our capture, and have the chosen mitigation working.

**If the gate fails:** Use the accessibility screenshot path (about 3 frames per second, no consent dialog) as the main capture; accept slower reactions.

## Phase 4.1: Screen capture

### 4.1.1 Background service and capture permission

**Goal:** A Guard service that can hold screen-capture permission and survive normal use.

**Do:**
1. Create the Guard as a foreground service of type "media projection", with the required permission and a persistent notification.
2. Build a transparent "consent" screen that asks Android for capture permission and hands the result to the service. Start the service in the foreground **before** using the permission.
3. Register the "capture stopped" callback before starting capture; when it fires, move to an **awaiting permission** state and show a "Resume Veil" notification action that reopens the consent screen.
4. Ask for the **entire screen** (not a single app), and detect if the user picked a single app anyway.
5. Test on the iQOO: what happens on lock/unlock, on tapping the status-bar chip, on killing the app.
6. Test the demo shortcut: `adb shell appops set <package> PROJECT_MEDIA allow`. Check whether it skips the dialog and survives lock on this phone, and record the result.

**Produces:** The capture service, a behaviour table in `docs/reports/ch4-plumbing.md`.

**Done when:** Capture starts, stops cleanly, recovers through the notification, and lock behaviour is documented.

### 4.1.2 Small frames, cheaply

**Goal:** Frames at the Guard's working size with minimal copying.

**Do:**
1. Create the virtual display at **360 × 800** (one third of a 1080 × 2400 panel; match the real aspect ratio).
2. Receive frames through an image reader that hands out hardware buffers (shareable with the GPU and AI chip without copying); always take only the latest frame and release it immediately.
3. Handle rotation by resizing the display.
4. Implement **pause** (detach the output surface) and **resume**. Pausing keeps the permission.
5. Measure frames delivered per second on a static screen, while scrolling, and during video.

**Produces:** A `ScreenSource` that emits frames, plus measurements.

**Done when:** A static screen delivers close to zero frames, and pause/resume works without asking permission again.

### 4.1.3 Backup capture and blind spots

**Goal:** A fallback capture path and a list of what we can't see.

**Do:**
1. Implement the accessibility-screenshot capture path (no consent dialog; limited to about one shot every 333 ms; full resolution, so downscale it).
2. Make the capture path switchable from settings.
3. Test which apps appear black: Netflix, Prime Video, Chrome Incognito, banking apps, Instagram DMs, YouTube. Record a compatibility table.
4. Design the "blind" handling: if a large black area sits over a video element, mark it blind; the text lane still works there.

**Produces:** The backup capture, a compatibility table.

**Done when:** Both paths deliver frames, and the table covers at least 8 apps.

### Proof test: Phase 4.1 · "Watch the watcher"

**Proves:** The phone can capture its own screen reliably through everyday events.

**Runs on:** The iQOO and the laptop (scrcpy, driver scripts).

**Idea:**
1. A driver script plays a 5-minute routine: 30 s idle; scroll Instagram; play a YouTube video; rotate the phone; lock and unlock; tap the capture chip in the status bar; kill the Guard; open Netflix.
2. The Guard saves every frame it captures, with timestamps. scrcpy records the real screen at the same time.

**It should check:**
- Captured frames show the same content as the real screen at the same moments.
- Almost no frames arrive while idle.
- Frames are the right size in both orientations.
- After a lock or kill, "Resume Veil" appears and restores capture.
- Netflix appears black and is reported as blind.
- Memory stays flat.

**Passes when:** AC-4.1-01 to AC-4.1-08 hold for this routine.

**Evidence:** The scrcpy recording, the captured frames, and the Guard's state log.

### Acceptance contract: Phase 4.1

**Entry conditions:** Phase 1.1 accepted.

**Deliverables:**
- The Guard's capture service, consent screen and "Resume Veil" notification action
- The screen source that emits 360 × 800 frames, with pause and resume
- The backup capture path (accessibility screenshots), switchable at runtime
- A lock-behaviour table and an app compatibility table in `docs/reports/ch4-plumbing.md`

**Acceptance criteria:**

| ID | Criterion | Pass threshold | How verified |
| --- | --- | --- | --- |
| AC-4.1-01 | Right size | Frames arrive at 360 × 800 (matching the panel's aspect ratio) in both orientations | Frame log |
| AC-4.1-02 | Quiet when still | A static screen delivers ≤ 1 frame per second | Frame counter |
| AC-4.1-03 | No leaks | 10 minutes of scrolling: memory growth ≤ 5%, no unreleased frames | Memory log |
| AC-4.1-04 | Recovery | When capture stops, the awaiting-permission state appears within 1 s; "Resume Veil" restores capture 10 out of 10 times | Test log |
| AC-4.1-05 | Pause keeps permission | Pause and resume 10 times with no new permission dialog | Test log |
| AC-4.1-06 | Lock behaviour known | Outcomes of lock/unlock, status-bar chip tap and app kill recorded; the permission-shortcut result recorded | Behaviour table |
| AC-4.1-07 | Backup path works | Accessibility-screenshot capture delivers ≥ 2 frames/s and can be switched on without a restart | Test log |
| AC-4.1-08 | Blind spots known | ≥ 8 apps tested for black frames | Compatibility table |

**Guarantees to later phases:**
- Frames arrive only when the screen changes, at the agreed size, and must be released by whoever receives them.
- Capture states (running, paused, stopped with a reason, awaiting permission) are fixed and reported.

**Out of scope:** Scroll events, drawing covers, any AI.

**Sign-off:** Owner C, verifier D. Evidence in `docs/acceptance/4.1.md`.

**If rejected:** If main capture is unreliable on the iQOO, make the backup path the default and record the slower reaction time for Chapters 2 and 5.

## Phase 4.2: Screen signals

### 4.2.1 Accessibility service and event logger

**Goal:** Know when things scroll, change, or switch apps, and log it for chapter 2.

**Do:**
1. Create the accessibility service declaring: scroll events, window state changes, window content changes, window list changes; permission to read window content; permission to take screenshots; interactive windows; an event timeout around 50 ms.
2. Sideload flow: document and test the "Allow restricted settings" step for this phone.
3. Turn events into the `UiEvent` contract: `Scrolled`, `WindowChanged`, `ContentChanged`, `ScreenOff/On`.
4. Add a **logging mode** that writes events to JSONL with the same clock as screen recordings, and hand it to the chapter 2 owner.
5. Track the foreground app, for the skip list.

**Produces:** The accessibility service, an event log format, sample logs.

**Done when:** A recorded session produces a clean event log that lines up with its video.

### 4.2.2 Accurate scrolling

**Goal:** Know exactly how far content moved, in every major app.

**Do:**
1. Normalise direction: report how far **content** moved on screen (opposite sign to Android's scroll delta).
2. For apps built with Jetpack Compose (which report absolute positions, not deltas), compute the difference per scrolling element.
3. Check accuracy against video in Instagram, YouTube, Chrome, Reddit and WhatsApp: compare reported scroll with the actual pixel shift.
4. Add a fallback for apps with no scroll events: estimate the shift from frame differences.

**Produces:** Scroll accuracy table per app.

**Done when:** Average error is under 8 pixels per scroll in the main apps, or the fallback covers the gaps.

### 4.2.3 Bounded layout snapshot

**Goal:** Get the positions of images, videos and text on screen without slowing the app being watched.

**Do:**
1. Never walk the app's layout tree inside the event callback. Instead, offer a **pull** snapshot with a time budget (40 ms) and a node limit (300), called by the Gatekeeper at most every 250 ms.
2. Extract image, video and web-content elements with their bounds, and visible text with bounds.
3. Note the limits: apps may not label images, and video surfaces are often missing. Keep pixel-based pieces as well.
4. Measure the snapshot's cost and check that the watched app does not stutter.

**Produces:** The snapshot function, a cost table.

**Done when:** Snapshots finish within budget and app smoothness is unchanged in a side-by-side check.

### Proof test: Phase 4.2 · "Scroll ruler"

**Proves:** The Guard knows exactly how far content moved, in our test app and in real apps, without slowing them down.

**Runs on:** The iQOO (Test Feed app in ruler mode; Instagram, YouTube, Chrome) and the laptop.

**Idea:**
1. In the Test Feed app, which logs its own true scroll position, a driver script performs 100 scrolls and flings at varied speeds.
2. Compare the Guard's reported scroll with the app's true position.
3. Repeat in Instagram, YouTube and Chrome, measuring the true movement from the screen recording.
4. Run the same scrolling with the Guard's service on and off, and compare dropped frames.

**It should check:**
- Distance and direction match.
- Events arrive on time.
- The watched app does not stutter more with the service on.
- Layout snapshots stay within their time budget.

**Passes when:** AC-4.2-02 to AC-4.2-06 hold.

**Evidence:** The comparison report, frame statistics, and a Perfetto trace.

### Acceptance contract: Phase 4.2

**Entry conditions:** Phase 1.1 accepted.

**Deliverables:**
- The accessibility service with its configuration
- The mapping from Android events to `UiEvent`, plus logging mode (JSONL)
- The scroll accuracy table per app
- The bounded layout snapshot function and its cost table
- The tested restricted-settings steps in `docs/`

**Acceptance criteria:**

| ID | Criterion | Pass threshold | How verified |
| --- | --- | --- | --- |
| AC-4.2-01 | Events valid | 1,000 logged events all validate against the `UiEvent` contract | Validation script |
| AC-4.2-02 | Scroll accurate | Mean error ≤ 8 px per scroll in Instagram, YouTube and Chrome; direction correct in 100% of checked cases | Accuracy table |
| AC-4.2-03 | Logger in sync | Logged scrolls within ± 1 frame of the screen recording | Spot check |
| AC-4.2-04 | Snapshot within budget | p95 ≤ 40 ms, ≤ 300 nodes, called at most once every 250 ms | Trace |
| AC-4.2-05 | No tree walks in callbacks | Zero layout-tree walks inside event handling | Code review and trace |
| AC-4.2-06 | Watched app stays smooth | Instagram dropped-frame rate with the service on vs off differs by ≤ 1 percentage point | Frame stats |
| AC-4.2-07 | Right app known | Foreground app correct across 20 app switches | Test log |
| AC-4.2-08 | Sideload setup works | Restricted-settings steps written and tested on the iQOO | Doc and screenshots |

**Guarantees to later phases:**
- Scroll events report how far **content** moved on screen, in screen pixels, on the shared clock.
- The layout snapshot never exceeds its budget and is only ever pulled, never pushed.

**Out of scope:** Frames, drawing, AI.

**Sign-off:** Owner C, verifier B (the scroll data feeds B's Chapter 2 work). Evidence in `docs/acceptance/4.2.md`.

**If rejected:** For apps with poor scroll events, enable the frame-difference fallback and list those apps as "estimated scroll" for Chapters 2 and 5.

## Phase 4.3: Drawing covers

### 4.3.1 Overlay window

**Goal:** Draw covers on top of every app without blocking touches.

**Do:**
1. Create an **accessibility overlay** window from the accessibility service: no extra permission, drawn above the keyboard and status bar, touches pass through.
2. Implement cover styles: solid, mosaic (from the last captured frame's crop), blur effect, optional label.
3. The renderer takes a `MaskPlan` and redraws only when it changes.
4. Handle rotation, the status bar, cutouts and split screen.

**Produces:** The `OverlayRenderer`.

**Done when:** Covers render over Instagram, YouTube, Chrome and the keyboard, and taps pass through to the app below.

### 4.3.2 Glued test box

**Goal:** Prove covers can follow content using scroll events alone.

**Do:**
1. Debug mode: tap a point to place a red box there.
2. Move the box on every scroll event by the reported distance.
3. Record a 30-second scroll session in each major app and measure drift between the box and the item it started on.
4. Fix sign errors, timing offsets and container mismatches (scrolls inside nested lists).

**Produces:** Drift measurements per app.

**Done when:** Drift stays under 8 pixels over 30 s in the main apps.

### 4.3.3 Self-capture test and peeking

**Goal:** Settle the "we see our own covers" problem on the real phone.

**Do:**
1. Confirm whether covers appear in captured frames (expected: yes).
2. Have the renderer publish where it drew covers, and attach those areas to each frame (`ownOverlay`), so later stages treat them as "unknown", not as content.
3. Test whether a per-window screenshot (which excludes our overlay) is available on this phone and how often it can be called. If it works, it becomes the "peek" used to double-check before uncovering.
4. Add the long-press gesture on a cover (for "peek" and "that's not it" in chapter 6).
5. Write the chapter report and apply the gate.

**Produces:** The self-capture findings, the chosen mitigation, the gesture hook, the gate decision.

**Done when:** The mitigation is chosen and demonstrated, and the gate decision is recorded.

### Proof test: Phase 4.3 · "Sticky note"

**Proves:** Covers stay glued to their items, never get in the user's way, and we understand self-capture.

**Runs on:** The iQOO (Test Feed app) and the laptop (scrcpy recording).

**Idea:**
1. In debug mode, place covers on 3 known items in the Test Feed app.
2. A driver script scrolls up and down for 30 s, flings, then stops.
3. Tap through a cover onto a button underneath it (the Test Feed app logs the tap).
4. Long-press a cover.
5. Save the captured frames while covers are visible.

**It should check:**
- Drift between each cover and its item stays small, using the item's true position from the app's log.
- Taps reach the app underneath.
- The long-press is caught.
- The saved frames show whether our covers are captured, and the reported cover positions line up with them.

**Passes when:** AC-4.3-01 to AC-4.3-07 hold.

**Evidence:** The scrcpy recording, the drift report, the tap log, and the captured frames.

### Acceptance contract: Phase 4.3 (includes the Chapter 4 gate)

**Entry conditions:** Phases 4.1 and 4.2 accepted.

**Deliverables:**
- The overlay renderer with solid, mosaic, blur and label styles
- The glued-box debug mode and the drift table
- Self-capture findings with example frames, own-cover position reporting, and peek findings
- The long-press hook on covers
- The completed `docs/reports/ch4-plumbing.md`

**Acceptance criteria:**

| ID | Criterion | Pass threshold | How verified |
| --- | --- | --- | --- |
| AC-4.3-01 | On top, not in the way | Covers draw above apps, the keyboard and the status bar; taps pass through in 5 apps | Test log |
| AC-4.3-02 | Fast drawing | A new cover plan is visible within 1 display frame (p95) | Trace |
| AC-4.3-03 | Glued | Drift ≤ 8 px over 30 s of scrolling in the main apps | Drift table |
| AC-4.3-04 | Self-capture settled | Whether our covers appear in our own capture is proven with example frames | Report |
| AC-4.3-05 | Own covers reported | Every frame captured while covers are visible carries their positions, accurate to within 2 px at capture scale | Frame log check |
| AC-4.3-06 | Peek known | Per-window screenshot availability and rate limit documented; if available, shown to exclude our covers | Report |
| AC-4.3-07 | Long-press works | A long-press on a cover is detected, and normal taps still reach the app below | Test log |

**Guarantees to later phases:**
- The overlay takes a cover plan and draws it within one frame.
- Positions of our own covers come attached to every frame, so the brain can treat them as "unknown".
- Long-press events on covers are delivered for peeking and corrections.

**Out of scope:** Deciding what to cover.

**Sign-off:** Owner C; verifiers B (self-capture handling feeds the tracker) and D (touch behaviour from a user's view). Evidence in `docs/acceptance/4.3.md`.

**If rejected:** Apply the Chapter 4 fallback, and if self-capture cannot be handled, switch to solid covers with longer holds (as in the Chapter 2 fallback).

---

# Chapter 5: GUARD

**The question:** Does the full Guard (when to look, finding, judging, steady covers) work live on the real phone, fast and light enough to use every day?

**Depends on:** Gates of chapters 2, 3 and 4.

**Chapter gate (target):**
- a cat in a live Instagram feed is covered within **0.3 s** (95% of the time) in Balanced mode;
- no visible stutter in Instagram with the Guard on;
- memory under **3 GB**;
- **15% or less extra battery** over 30 minutes of Instagram at fixed brightness.

**If the gate fails:** Move to Light defaults, smaller models, fewer looks per second, and UI-layout pieces plus tiles instead of the object finder.

## Phase 5.1: Port the brain

### 5.1.1 Kotlin decision logic

**Goal:** The same Gatekeeper, Tracker, Planner, Memory and Judge on the phone.

**Do:**
1. Create a plain Kotlin module (no Android dependencies) with the contract types and: change detector, scheduler, tracker, mask planner, cache, judge.
2. Keep the same rules as Python: whole-number geometry, time passed in, fixed tie-breaking, same parameter tables per mode.
3. The Judge does its maths in 64-bit floating point on both sides.

**Produces:** `guard/brain/` module.

**Done when:** It compiles and its own unit tests pass on a laptop JVM.

### 5.1.2 Golden tape tests

**Goal:** Prove phone and laptop brains behave identically.

**Do:**
1. Run every golden tape from chapter 2 through the Kotlin brain.
2. Exact match required for the change detector, scheduler, tracker, planner and cache hit sequence.
3. Judge: decisions must match exactly except within 0.001 of a threshold; probabilities within a tiny tolerance.
4. Add a separate model-parity test for AI outputs: phone and laptop fingerprints must agree (cosine at least 0.98) and decisions at least 99% of the time.
5. Run tape tests automatically on every change (CI on a laptop).

**Produces:** Tape test suite and CI job.

**Done when:** All tapes pass.

### 5.1.3 Teacher and storage on the phone

**Goal:** Turn the user's words and photos into concept cards on the device.

**Do:**
1. Run both text encoders on the phone (SigLIP2's, and the object finder's own) to build concept cards when the list changes. Never during looks.
2. Lookalike lists: start with a packaged vocabulary of everyday nouns; pick the nearest few that are not synonyms of the concept.
3. Example photos: fingerprint them on the phone, store the average, and give them their own threshold.
4. Store settings, concept cards and corrections in an encrypted local database.
5. Apply new concept cards without restarting the Guard.

**Produces:** On-device Teacher and the encrypted store.

**Done when:** Typing "spiders" in a debug screen produces a working concept card in under 1 s (target).

### Proof test: Phase 5.1 · "Same brain on the phone"

**Proves:** The Kotlin brain, running on the actual phone, makes the same decisions as the Python twin.

**Runs on:** The iQOO (an instrumented test) and the laptop.

**Idea:**
1. Run every golden tape through the brain on the phone itself, not only in laptop CI.
2. Type 5 concepts into a debug screen on the phone and export the resulting concept cards. Build the same cards in the Workshop and compare.
3. Restart the phone and check that settings and corrections are still there. Pull the store file and try to open it without the key.

**It should check:**
- Identical outputs on every tape.
- Concept cards match.
- Storage is encrypted and survives a restart.

**Passes when:** AC-5.1-01 to AC-5.1-07 hold.

**Evidence:** The on-device test report, the card comparison, and a screenshot of the failed attempt to open the store.

### Acceptance contract: Phase 5.1

**Entry conditions:** Phases 2.3 (golden tapes) and 1.3 (Judge and concept card format) accepted.

**Deliverables:**
- `guard/brain/`: a plain Kotlin module with the contract types, change detector, scheduler, tracker, mask planner, cache and Judge
- The tape test suite running in laptop CI
- The phone-vs-laptop model parity test
- The on-device Teacher and the encrypted store

**Acceptance criteria:**

| ID | Criterion | Pass threshold | How verified |
| --- | --- | --- | --- |
| AC-5.1-01 | Tapes pass | 100% of golden tapes give an exact match for the change detector, scheduler, tracker, planner and cache-hit sequence | CI |
| AC-5.1-02 | Judge matches | Decisions are identical except within 0.001 of a threshold | CI |
| AC-5.1-03 | Portable | The brain module has no Android dependencies and runs in laptop CI | Build configuration; CI |
| AC-5.1-04 | Teacher is fast | A new concept card is ready on the phone in ≤ 1 s | Timing log |
| AC-5.1-05 | Teacher matches | Phone prompt fingerprints vs Python: cosine ≥ 0.99 per prompt | Parity test |
| AC-5.1-06 | Stored safely | The store file is unreadable without the key; settings and corrections survive a restart | Test log |
| AC-5.1-07 | Live changes | A list change takes effect in ≤ 1 s, with no restart | Test log |

**Guarantees to later phases:**
- The phone's brain behaves exactly like the twin, so any tuning done in the twin transfers to the phone unchanged.
- Concept cards built on the phone match cards built in the Workshop.

**Out of scope:** Live capture and wiring (5.2), performance (5.3).

**Sign-off:** Owner B, verifier A. Evidence in `docs/acceptance/5.1.md`.

**If rejected:** Fix the port. Golden tapes are never edited to make the port pass, unless a genuine twin bug is found; in that case fix the twin, regenerate the tapes, and reopen Phase 2.3.

## Phase 5.2: Wire it together

### 5.2.1 The conductor

**Goal:** Run every look in the right order, never piling up.

**Do:**
1. One coordinator connects: frame → change detector → scheduler → (if a look is due) find pieces → fingerprint new pieces → judge → tracker → mask planner → overlay.
2. AI calls run one at a time on a single worker. If a look is running when a new frame arrives, skip the frame.
3. Scroll events go straight to the tracker and overlay, with no AI.
4. Publish stats after each look (looks per second, AI time, cache hits, active covers, skipped frames).
5. Pause everything when the screen is off or a skipped app is in front.

**Produces:** The working Guard pipeline.

**Done when:** Pointing the phone at a cat photo in Instagram produces a cover, and scrolling moves it.

### 5.2.2 Pieces from three sources

**Goal:** Find every relevant piece of the screen.

**Do:**
1. Pieces from the **UI layout** snapshot (images, videos, posts).
2. Pieces from the **object finder** (things inside photos), with its own fingerprints judged against its own concept cards.
3. Pieces from **tiles** (for whole-post concepts and apps with no layout information).
4. Merge duplicates by overlap.
5. Crop and resize all new pieces on the GPU into one batch for the Describer; check memory first and only fingerprint misses.
6. For thumbnail grids (Explore), batch up to 16 thumbnails into one AI call.

**Produces:** The region proposer on the phone.

**Done when:** Small cats in grid thumbnails are caught in the live Explore view.

### 5.2.3 Layer 1 and the text lane

**Goal:** Always-on safety and text filtering live on the phone.

**Do:**
1. Run NudeNet 320n on every look, and 640m in Balanced and Strict.
2. Layer 1 rules: cover on first sighting, solid style, no peeking, longer hold.
3. Text: read visible text from the layout snapshot first; use ML Kit OCR only for text inside images.
4. Run the toxicity model only on **new** text; apply keyword rules from concept cards ("spoiler" names, etc.).
5. Text findings cover the whole post or message.

**Produces:** Layer 1 and the text lane in the pipeline.

**Done when:** A test page with abusive comments and a test set of safe-for-work proxy images trigger the expected covers.

### Proof test: Phase 5.2 · "The cat feed"

**Proves:** The whole Guard works live, end to end.

**Runs on:** The iQOO (first the Test Feed app with a known mix of cats, spiders, lookalikes and clean posts; then real Instagram) and the laptop.

**Idea:**
1. Load the Test Feed app with a known content set. A driver script scrolls through it at human-like speed with the Guard on, in Balanced mode.
2. The Guard writes its debug log (every look, finding and cover, with timestamps). The Test Feed app logs where every item was at every moment.
3. A checker script compares the two logs.
4. Repeat with Layer 1 test images and a page of abusive comments.
5. Turn the screen off for a minute, and open an app on the skip list.
6. Finally, a 5-minute manual session in real Instagram, recorded with scrcpy.

**It should check:**
- Every cat and spider is covered while on screen.
- No clean or lookalike post is covered.
- Covers follow scrolling.
- Nothing happens in a skipped app or with the screen off.
- Layer 1 covers are solid and cannot be peeked.
- Abusive text is covered.

**Passes when:** AC-5.2-01 to AC-5.2-07 hold and the checker report is clean.

**Evidence:** The checker report, both logs, and the scrcpy recordings.

### Acceptance contract: Phase 5.2

**Entry conditions:** Phases 5.1, 3.3 and 4.3 accepted.

**Deliverables:**
- The conductor that runs the full look on the phone
- The on-device region proposer (layout, finder, tiles) with batching
- Layer 1 and the text lane live on the phone
- Stats published after every look
- An on-device replay mode: a video file and scripted events instead of live capture

**Acceptance criteria:**

| ID | Criterion | Pass threshold | How verified |
| --- | --- | --- | --- |
| AC-5.2-01 | Works live | A cat in a live Instagram feed is covered; the cover follows scrolling; covers clear on app switch | Recorded demonstration |
| AC-5.2-02 | Respects off states | 0 looks with the screen off and in skipped apps | Stats log |
| AC-5.2-03 | Never queues | No backlog under load; skipped frames counted | Trace |
| AC-5.2-04 | All piece sources used | Layout, finder and tiles each produce pieces on Instagram; Explore thumbnails batched ≤ 16 per AI call | Stats; trace |
| AC-5.2-05 | Layer 1 live | Controlled test images get a solid cover on first sighting; peek is disabled for them | Test log |
| AC-5.2-06 | Text lane live | An abusive-comment test page is covered; OCR runs only on text inside images; toxicity runs only on new text | Counters; test log |
| AC-5.2-07 | Matches the twin | The same recording replayed on the phone gives cover plans matching the twin's (overlap ≥ 0.9 for ≥ 95% of covers) | Integration parity test |

**Guarantees to later phases:** A complete, working Guard whose behaviour matches the twin. Performance work in 5.3 only tunes it; it does not change what it decides.

**Out of scope:** Hitting the speed, smoothness and battery targets (5.3); the Console app (6.1).

**Sign-off:** Owner C; verifiers B (parity) and D (live behaviour from a user's view). Evidence in `docs/acceptance/5.2.md`.

**If rejected:** If AC-5.2-07 fails, find which stage diverges by replaying tapes stage by stage, and fix it on the phone side first.

## Phase 5.3: Real-world performance

### 5.3.1 Time to cover

**Goal:** Measure how quickly covers appear in real use.

**Do:**
1. Add timestamps at each stage and capture traces with Perfetto.
2. Measure time from content first appearing in a frame to the cover being drawn, across 100 appearances (scroll in, swipe, scene cut).
3. Find the slowest stage and fix it (smaller look area, batching, cache, model size).
4. Optional: film the screen with a second phone in slow motion for a sanity check.

**Produces:** A latency report with a per-stage breakdown.

**Done when:** p95 is under 0.3 s in Balanced, or the remaining gap and its fix are documented.

### 5.3.2 Smoothness, memory and heat

**Goal:** Prove the Guard doesn't make the phone worse to use.

**Do:**
1. Measure dropped frames in Instagram scrolling with the Guard on and off (Perfetto frame timeline or `dumpsys gfxinfo`).
2. Track memory (PSS) over 30 minutes.
3. Track temperature and confirm the Throttled state kicks in and recovers.
4. Check the Guard survives memory pressure and the system killing the app.

**Produces:** The smoothness and memory section of the chapter report.

**Done when:** No visible stutter difference, memory under 3 GB, and throttling observed working.

### 5.3.3 Battery test

**Goal:** Replace the battery estimate with a measurement.

**Do:**
1. Two 30-minute Instagram sessions, same brightness, same start charge, same network: Guard off vs Guard on (Balanced).
2. Record battery use with `dumpsys batterystats` and the battery percentage.
3. Repeat for Light and Strict, and for 15 minutes of video.
4. Tune default rates if over budget.
5. Write `docs/reports/ch5-guard.md` and apply the chapter gate.

**Produces:** Measured battery cost per mode.

**Done when:** The measured numbers are recorded and the gate decision is made.

### Proof test: Phase 5.3 · "A day in 30 minutes"

**Proves:** The Guard is fast, smooth and light enough for everyday use.

**Runs on:** The iQOO and the laptop (`batterystats`, Perfetto, `gfxinfo`).

**Idea:**
1. Charge to the same level, fix the brightness, and use the same network. A driver script scrolls Instagram at a human-like pace for 30 minutes with the Guard off, then 30 minutes with the Guard on (Balanced). Repeat both runs once more.
2. During the "on" runs, record traces, memory and temperature.
3. Using the Test Feed app's timestamps, measure the time from an item appearing to its cover being drawn, over 100 items.
4. Kill the Guard 5 times during a session.

**It should check:**
- The battery difference between "off" and "on".
- Dropped frames with the Guard on vs off.
- Memory stays flat and under 3 GB.
- Throttling kicks in when hot and recovers.
- Time-to-cover p95.
- Recovery after each kill.

**Passes when:** AC-5.3-01 to AC-5.3-07 hold.

**Evidence:** Battery statistics from all four runs, traces, and memory and thermal logs.

### Acceptance contract: Phase 5.3 (includes the Chapter 5 gate)

**Entry conditions:** Phase 5.2 accepted.

**Deliverables:**
- Perfetto traces and the latency report with a per-stage breakdown
- The smoothness, memory and heat section
- The battery table per mode
- Tuned default parameters, copied back into the twin
- `docs/reports/ch5-guard.md`

**Acceptance criteria:**

| ID | Criterion | Pass threshold | How verified |
| --- | --- | --- | --- |
| AC-5.3-01 | Time to cover | p95 ≤ 0.3 s across 100 appearances, Balanced | Latency report |
| AC-5.3-02 | No stutter | Instagram dropped-frame rate with the Guard on vs off differs by ≤ 1 percentage point | Frame stats |
| AC-5.3-03 | Memory | App memory (PSS) ≤ 3 GB throughout 30 minutes; growth ≤ 5% | Memory log |
| AC-5.3-04 | Heat handled | The Throttled state is entered when the phone is hot and left when it cools | Trace |
| AC-5.3-05 | Battery | ≤ 15% extra over 30 minutes of Instagram in Balanced; A/B run twice with the same brightness, starting charge and network | Battery table |
| AC-5.3-06 | All modes measured | Light, Strict and a 15-minute video session measured and recorded | Battery table |
| AC-5.3-07 | Survives being killed | Back to running, or showing "Resume Veil", within 5 s, 5 out of 5 times | Test log |
| AC-5.3-08 | Twin kept in step | Every tuned parameter is updated in the twin, and the golden tapes still pass | CI |

**Guarantees to later phases:** Measured performance numbers that the final report and the pitch may quote as-is.

**Out of scope:** The Console app, corrections, topic packs.

**Sign-off:** Owner C, verifier A (repeats the battery A/B independently). Evidence in `docs/acceptance/5.3.md`.

**If rejected:** Apply the Chapter 5 fallback (Light defaults, smaller models, fewer looks, no finder), re-measure, and record what was given up.

---

# Chapter 6: PRODUCT

**The question:** Can a real person install Veil, set it up, teach it their dislikes, correct it, and trust it, and can we demo it convincingly?

**Depends on:** Phase 6.1 can start immediately against a fake Guard. Phases 6.2 and 6.3 need chapter 5.

**Chapter gate (target):** A person who has never seen Veil installs it, grants permissions, adds two dislikes, and sees them covered in Instagram, without help. The full demo runs three times in a row without a failure.

## Phase 6.1: The Console app (Flutter)

### 6.1.1 Bridge to the Guard

**Goal:** The app can control the Guard and see its state, even when the app was closed and reopened.

**Do:**
1. Define the bridge with Pigeon: commands (start, stop, set mode, set skip list, set concept pack, compile pack, submit feedback, request permissions) and two event streams (engine state with permissions; stats ticks about once a second).
2. Large data (concept packs, example photos) moves as **files**; only a path and checksum cross the bridge.
3. The Guard restores itself from its own saved settings. The app only reads and changes them.
4. Hide the generated bridge behind the app's own interface, and build a **fake Guard** so screens can be built and tested before chapter 5 is done.
5. All bridge calls hop off the main thread on the Android side.

**Produces:** Bridge definition, Kotlin and Dart bindings, the fake Guard.

**Done when:** The app shows live state from the fake Guard and, later, from the real one.

### 6.1.2 Onboarding and permissions

**Goal:** Get a new user from install to protected, clearly and honestly.

**Do:**
1. Explain what Veil does and that nothing leaves the phone (a prominent disclosure screen with clear consent).
2. Walk through enabling the accessibility service, including the "Allow restricted settings" step for sideloaded installs (open App info for them).
3. Ask for screen-capture permission (entire screen), and explain why it is asked again after locking the phone.
4. Ask for notification permission (for the "Resume Veil" action).
5. Show a status screen that tells the user exactly what is missing if anything is.

**Produces:** Onboarding flow.

**Done when:** Three people who have never used it complete onboarding without help.

### 6.1.3 Main screens

**Goal:** Everything the user needs day to day.

**Do:**
1. **Concept Studio:** add a dislike by typing, optionally add example photos, see the generated "looks like / but not" lists, choose cover style, turn concepts on/off.
2. **Strictness:** Light / Balanced / Strict with a plain explanation of the trade-offs (speed of covering vs battery vs false covers).
3. **Skip list:** apps where Veil does nothing.
4. **Live stats:** looks per second, covers on screen, AI time, estimated battery impact.
5. **Recent covers:** a short history (with small thumbnails stored on the phone only) where the user can mark "correct", "not this" or "missed one".
6. Accessibility of the app itself: readable sizes, screen-reader labels, dark mode.

**Produces:** The complete Console app.

**Done when:** Every screen works against the real Guard.

### Proof test: Phase 6.1 · "First-time user"

**Proves:** A real person can set up and use Veil without help.

**Runs on:** The iQOO (fresh install), with an observer.

**Idea:**
1. Uninstall everything and clear all data. Hand the phone to someone who has never seen Veil and say only: "Make it hide cats."
2. The observer notes every hesitation, wrong tap or question, and does not help.
3. Separately, run the Flutter on-device integration tests against the real Guard: every screen and action, plus killing and reopening the app.

**It should check:**
- The person finishes setup unaided.
- Every permission step is understood.
- After reopening, the app shows the Guard's correct state.
- Every screen action actually reaches the Guard.

**Passes when:** AC-6.1-01 to AC-6.1-08 hold, with 3 different people.

**Evidence:** Observer notes, scrcpy recordings, and the integration test report.

### Acceptance contract: Phase 6.1

**Entry conditions:** Phase 1.1 accepted for building against the fake Guard. Criteria marked "real Guard" also need Phase 5.2 accepted.

**Deliverables:**
- The Pigeon bridge definition with generated Kotlin and Dart bindings
- The fake Guard
- Onboarding, Concept Studio, Strictness, Skip list, Live stats and Recent covers screens
- Widget tests that run against the fake Guard

**Acceptance criteria:**

| ID | Criterion | Pass threshold | How verified |
| --- | --- | --- | --- |
| AC-6.1-01 | Bridge complete | Every command round-trips against the fake Guard and the real Guard; the protocol version is checked on connect | Integration tests |
| AC-6.1-02 | Reopens correctly | After the app is killed and reopened, it shows the Guard's correct state within 1 s (real Guard) | Test log |
| AC-6.1-03 | Files, not channels | Packs and photos move as files; a corrupted file is rejected and the previous pack stays active | Test |
| AC-6.1-04 | Onboarding works | 3 first-time users finish setup without help (real Guard) | Observation notes |
| AC-6.1-05 | Missing pieces explained | Each missing permission is shown with a one-tap fix | Test log |
| AC-6.1-06 | Screens work | Every action on every main screen works with the real Guard; widget tests pass against the fake | Tests |
| AC-6.1-07 | Accessible | Every control has a screen-reader label; text at 200% size does not clip | Checklist |
| AC-6.1-08 | No stray network | The only network calls go to Workshop endpoints | Network log |

**Guarantees to later phases:** A stable app interface for corrections (6.2) and the demo (6.3).

**Out of scope:** The correction logic itself and the Workshop server (6.2).

**Sign-off:** Owner D, verifier C. Evidence in `docs/acceptance/6.1.md`.

**If rejected:** Fix the failing screens or flows. Onboarding failures are fixed by changing wording or flow and re-testing with 3 new people, not the same ones.

## Phase 6.2: Learning and packs

### 6.2.1 Corrections

**Goal:** Users can fix mistakes, and the Guard remembers.

**Do:**
1. Long-press a cover: "Peek" (Layer 2 only) or "That's not it".
2. "That's not it" stores the item's fingerprint as an exception for that concept (up to 64 per concept, oldest dropped) and raises that concept's threshold slightly (+0.02 per correction, capped at +0.15 total).
3. "Missed one" (from Recent covers or a screenshot) lowers the threshold slightly, with the same cap.
4. Layer 1 cannot be changed by corrections.
5. Everything stays in the encrypted store on the phone.
6. Test scenario: a fox gets covered as a cat; after one correction, the same fox photo and its reposts stay uncovered, while real cats are still covered.

**Produces:** The correction loop end to end.

**Done when:** The test scenario passes.

### 6.2.2 Workshop server (Flask)

**Goal:** Serve models and topic packs, and receive only opt-in aggregate data.

**Do:**
1. Endpoints:
    - model catalogue (signed manifests with file links and checksums);
    - topic pack list and download;
    - **opt-in** "compile my words" (only the typed words, shown to the user before sending);
    - **opt-in** aggregate metrics;
    - developer-only evaluation runs.
2. Every opt-in request body rejects unknown fields, so screen content can't sneak in by mistake.
3. Never log request bodies for opt-in endpoints; no device or account identifiers; metrics only as counts and buckets.
4. Sensitive packs (for example recovery-related) download as one bundle, so the server can't tell which one a user picked.
5. The app re-checks every downloaded file's checksum and schema before use.

**Produces:** `workshop/api/` running locally and on a small server.

**Done when:** The app can download a pack and a model update from it, and privacy tests (unknown fields rejected, nothing logged) pass.

### 6.2.3 Topic packs

**Goal:** Ready-made, tested packs for common needs.

**Do:**
1. Create 5 packs: Spiders, Needles and injections, Gore, Alcohol, and one spoiler pack (a TV show of the team's choice: names, images, keywords).
2. For each, write "looks like / but not" lists and keyword rules, then tune with the evaluation tools from chapters 1-2 on a small labelled set.
3. Record each pack's measured accuracy in its description.
4. Mark sensitive packs as such.

**Produces:** 5 packs in the Workshop catalogue.

**Done when:** Each pack meets at least 80% recall and fewer than 5% clean false covers on its own test set.

### Proof test: Phase 6.2 · "Not a cat"

**Proves:** Corrections work as a user expects, and privacy holds.

**Runs on:** The iQOO (Test Feed app with a fox post and a repost of it further down; PCAPdroid) and the laptop (Workshop server, Wireshark).

**Idea:**
1. Scroll to a fox that gets covered as a cat. Long-press it and choose "That's not a cat." Scroll away and back, then on to the repost of the same fox. Check a real cat further down the feed.
2. Record all network traffic on the phone during this, with PCAPdroid.
3. Send the Workshop server deliberately bad requests: extra fields shaped like screen content, missing consent, tampered pack files.
4. Install the Spiders pack from the server and scroll a spider feed.

**It should check:**
- The fox and its repost stay uncovered; real cats are still covered.
- Zero network traffic during the correction.
- The server rejects bad requests and logs no request bodies.
- The app refuses tampered files.
- The installed pack works.

**Passes when:** AC-6.2-01 to AC-6.2-07 hold.

**Evidence:** The scrcpy recording, the network capture, server logs, and the pack test report.

### Acceptance contract: Phase 6.2

**Entry conditions:** Phase 5.2 accepted (for corrections) and the 6.1.1 bridge working.

**Deliverables:**
- The correction loop end to end (long-press, exceptions, threshold nudges)
- `workshop/api/` running locally and on a small server, with privacy tests
- 5 topic packs in the Workshop catalogue, each with measured accuracy

**Acceptance criteria:**

| ID | Criterion | Pass threshold | How verified |
| --- | --- | --- | --- |
| AC-6.2-01 | Fox scenario | After one "not a cat" correction, the same fox photo and its reposts stay uncovered, and real cats are still covered | Recorded test |
| AC-6.2-02 | Limits hold | Threshold change capped at ± 0.15; ≤ 64 exceptions per concept; Layer 1 unaffected by corrections | Unit tests |
| AC-6.2-03 | Corrections stay local | 0 network requests during a correction | Network log |
| AC-6.2-04 | API to spec | Every endpoint returns the agreed shapes | API tests |
| AC-6.2-05 | Privacy enforced | Unknown fields are rejected without echoing input; opt-in endpoints refuse requests without consent; no request bodies appear in logs | Privacy tests; log inspection |
| AC-6.2-06 | Tamper-proof | The app rejects a manifest or pack with a bad signature or checksum | Test |
| AC-6.2-07 | Packs are good | 5 packs, each ≥ 80% recall and ≤ 5% clean false covers on its own test set; sensitive packs flagged | Eval reports |

**Guarantees to later phases:** Corrections, the Workshop server and the packs are ready for the demo and the final report.

**Out of scope:** Public release and store submission.

**Sign-off:** Owner D, verifier A (re-runs the pack evaluations). Evidence in `docs/acceptance/6.2.md`.

**If rejected:** Ship fewer packs: only the ones that pass go in the catalogue. Privacy criteria (AC-6.2-03, -05, -06) cannot be waived.

## Phase 6.3: Ship the demo

### 6.3.1 Hardening

**Goal:** Nothing embarrassing happens in front of an audience.

**Do:**
1. Recovery: the Guard restarts after a crash; the "Resume Veil" path after lock works every time.
2. Edge cases: rotation, split screen, keyboard open, picture-in-picture, notification shade, app switching mid-scroll.
3. Blind apps (Netflix and similar): show a small "can't see protected video" hint instead of failing silently.
4. Heat: confirm throttling under a 20-minute stress session.
5. Fix every bug found; keep a short known-issues list.

**Produces:** A stable build and known-issues list.

**Done when:** A 30-minute free-use session by someone outside the build team ends with no crash and no stuck cover.

### 6.3.2 Final evaluation

**Goal:** Honest numbers for the pitch.

**Do:**
1. Re-run the frozen test sets on the final build: screenshots (chapter 1), recordings (chapter 2).
2. Measure on the phone: time to cover, looks per second, AI time per look, memory, battery cost per mode.
3. Put the results in one page: `docs/reports/final.md`, with each number labelled as measured, and the conditions stated.

**Produces:** The final report.

**Done when:** Every claim in the pitch has a measured number behind it.

### 6.3.3 Demo and pitch

**Goal:** A convincing, repeatable demo and clear story.

**Do:**
1. Demo script:
    1. a normal Instagram feed;
    2. add "cats" in the Console;
    3. cats vanish while scrolling;
    4. switch to Strict;
    5. a "not a cat" correction on a fox;
    6. a spider pack from the catalogue;
    7. show airplane mode, to make the point that nothing leaves the phone.
2. Prepare the phone: sideloaded build, permissions granted, the capture-permission shortcut applied if it works on this phone, demo accounts with known content, brightness fixed, do-not-disturb on.
3. Record a backup video of the full demo in case anything fails live.
4. Pitch deck: problem, how it works (the six helpers), privacy story, measured numbers, limits (protected video, a short delay before covering), what's next.
5. Q&A sheet: battery, privacy, false covers, licences (Appendix C), Play Store path.
6. Rehearse three full runs; apply the chapter gate.

**Produces:** Demo build, backup video, deck, Q&A sheet.

**Done when:** Three consecutive rehearsals run cleanly.

### Proof test: Phase 6.3 · "Dress rehearsal"

**Proves:** The demo works every time, under real demo conditions.

**Runs on:** The demo phone and the presentation laptop.

**Idea:**
1. Run the full demo script start to finish three times in a row, recorded with scrcpy.
2. Hand the phone to someone outside the team for 30 minutes of free use.
3. Put the phone in airplane mode and repeat the core demo.
4. Play the backup video offline on the presentation laptop.

**It should check:**
- No step fails or needs a retry.
- No crash or stuck cover during free use.
- Everything works offline.
- Every number quoted matches the final report.

**Passes when:** AC-6.3-01 to AC-6.3-08 hold.

**Evidence:** Three rehearsal recordings, the free-use notes, and the airplane-mode recording.

### Acceptance contract: Phase 6.3 (includes the Chapter 6 gate)

**Entry conditions:** Phases 5.3, 6.1 and 6.2 accepted.

**Deliverables:**
- The hardened demo build and a known-issues list
- `docs/reports/final.md`
- The demo script, a backup demo video, the pitch deck, and the Q&A sheet
- The rehearsal log

**Acceptance criteria:**

| ID | Criterion | Pass threshold | How verified |
| --- | --- | --- | --- |
| AC-6.3-01 | Survives free use | A 30-minute session by someone outside the team ends with 0 crashes and 0 stuck covers | Session notes |
| AC-6.3-02 | Recovers | Crash, lock and kill recovery each pass 5 out of 5 times | Test log |
| AC-6.3-03 | Edge cases | Rotation, split screen, keyboard, picture-in-picture and the notification shade all checked | Checklist |
| AC-6.3-04 | Honest numbers | Every number in the final report is measured, with its conditions stated | Report review |
| AC-6.3-05 | Claims traceable | Every claim in the pitch points to a line in the final report | Deck review |
| AC-6.3-06 | Demo reliable | 3 consecutive clean rehearsals, including the airplane-mode step | Rehearsal log |
| AC-6.3-07 | Backup ready | The backup video plays offline on the presentation machine | Check on the day |
| AC-6.3-08 | Licences answered | The Q&A sheet answers every licence question in Appendix C | Review |

**Guarantees:** A demo that works, numbers that are true, and answers ready for hard questions.

**Out of scope:** Store release, commercial licensing.

**Sign-off:** Owner D; verifiers A, B and C (each watches one rehearsal). Evidence in `docs/acceptance/6.3.md`.

**If rejected:** Cut scope to cats plus one pack and rely on the backup video for anything unreliable. Never present a number that failed AC-6.3-04.

---

# Chapter 7: NAME ANYTHING

**Why this chapter:** the product promise is "type what you don't want to see, and it disappears". Chapters 1-6 tuned thresholds by hand for a few concepts (cats, spiders). An untuned word ("snakes") worked end to end but wrongly covered 53% of clean screens, because SigLIP2 scores sit at different levels for different words. This chapter replaces per-word tuning with automatic, label-free calibration, so that any concrete word works out of the box.

**Scope (user decision, 2026-10-06):**
- **In scope:** concrete visual nouns, named at the level a person would name them: one animal, object, food or vehicle ("buffalo", "umbrella", "pizza", "motorbike"). Finer subclasses inside a name (water buffalo vs cape buffalo) are not required.
- **Out of scope here:** abstract topics such as politics, violence or a specific person. These go through the text lane and topic packs.

**Chapter gate:** on a benchmark of never-tuned concrete words, at least 90% of the words reach recall ≥ 90% at a clean false-cover ≤ 5% (Balanced mode). Every number comes from public, human-labelled data; no word is hand-tuned.

## Phase 7.1: Self-calibrating concepts

### 7.1.1 Reference bank

**Goal:** a compact, safe, diverse picture of "everything else" that ships with the app.

**Do:**
1. Pick about 30,000 diverse, safe, permissively licensed public images (Open Images or COCO style), covering scenes, people, objects, screenshots, memes and text-heavy images. Exclude explicit material.
2. Compute their SigLIP2 image fingerprints on the laptop with the same exported model the phone uses. Store them as a compact asset (fp16 or int8; target ≤ 40 MB), with the source and licence for each image.
3. Write a builder script that recreates the asset from scratch.

**Produces:** the reference-bank asset, plus its builder and licence list.

**Done when:** the asset loads on the laptop twin and in Kotlin, and its fingerprints match a fresh recomputation (cosine ≥ 0.999).

### 7.1.2 Automatic threshold, competitors and prompt ensembles

**Goal:** a new word gets a correct threshold in under a second on the phone, with no labels.

**Do:**
1. **Prompt ensemble:** encode each word with several templates ("a photo of a {w}", "a {w}", "a close-up of a {w}", "a {w} in a meme", "a drawing of a {w}") and average them.
2. **Null calibration:** score the word against the whole bank. Almost every bank image is negative for any one word, so set the Balanced threshold at the bank quantile that gives the target clean false-cover; Light and Strict sit at fixed offsets. Exclude bank items whose labels include the word or one of its synonyms.
3. **Competitors:** find the nearest lookalike words automatically (text-embedding neighbours from a built-in vocabulary of about 5,000 concrete nouns). A cover fires only if the word beats its best competitor by a margin.
4. Implement it in the twin (Python) and in Kotlin. The golden-tape parity tests must keep passing.

**Produces:** auto-calibrated concept cards, in the twin and on the phone.

**Done when:** "snakes", which was never tuned, drops from 53% clean false-cover to ≤ 5% on the dev set, with recall reported.

### 7.1.3 "Also hide?" in the app

**Goal:** the user decides the edges of a word, not the model.

**Do:**
1. When a word is added, show the closest lookalike words as chips ("Also hide: bison? yak?"). Selected chips join the concept; unselected ones become competitors.
2. Show a small preview of what will be hidden: the top matches from the safe reference bank.
3. Adding a word must take under 1 s from typing to active.

**Produces:** the Console flow for adding any word.

**Done when:** a first-time user adds "buffalo" and sees it active, with chips, in under 1 s (phone).

### Proof test: Phase 7.1 · "Buffalo"
Type "buffalo" (never tuned) on the phone. Buffalo posts in the Test Feed and the public set get covered; cow and horse posts are not covered unless their chips are selected. On the laptop, the twin reports per-word recall and clean false-cover for 10 unseen words.

### Acceptance contract: Phase 7.1

| ID | Criterion | Pass threshold | How verified |
| --- | --- | --- | --- |
| AC-7.1-01 | Bank faithful | Fingerprint cosine ≥ 0.999 against a fresh recomputation | Script |
| AC-7.1-02 | Fast add | Word typed → concept active in ≤ 1 s on the phone | Phone timing |
| AC-7.1-03 | Unseen word sane | "snakes" clean false-cover ≤ 5% (was 53%) | Twin eval |
| AC-7.1-04 | Parity kept | Golden tapes still match exactly; Kotlin and twin thresholds agree to 1e-4 | Tests |
| AC-7.1-05 | Licences | Every bank image has a recorded permissive licence | Licence list |

## Phase 7.2: The "name anything" benchmark

### 7.2.1 Benchmark of unseen words

**Goal:** prove the 90% with data, not anecdotes.

**Do:**
1. From a public, human-labelled dataset with image-level labels (such as Open Images), pick 100 concrete words across animals, objects, foods and vehicles that were never used for tuning. Use ≥ 30 positive images per word, plus clean negatives that include lookalikes.
2. Add screenshot-style variants: crops placed into feed-like layouts at realistic sizes, so the numbers reflect phones, not photo galleries.
3. Freeze the set and record its hash. Words, images and labels are fixed before any method change.

**Produces:** the frozen benchmark with its licences.

**Done when:** the set is frozen and every label source is recorded.

### 7.2.2 Evaluate and improve

**Goal:** reach the gate, or learn exactly which words fail and why.

**Do:**
1. Run the twin on the benchmark: per-word recall, precision and clean false-cover in each mode, and the share of words meeting the gate.
2. Improve only the general method: templates, bank composition, quantile, competitor margin, crop sizes. Never tune a single word. Keep a log of each attempt; at most 5 test-set runs.
3. Port any changed parameters to Kotlin and re-run parity.

**Produces:** `docs/reports/ch7-name-anything.md`, with per-word results and a failure analysis (small objects, lookalikes, drawings).

**Done when:** the report shows the gate result honestly.

### 7.2.3 On the phone

**Goal:** the same behaviour on the phone.

**Do:**
1. Add 10 benchmark words on the phone and run the screenshot-style set through the replay harness. Results must match the twin within 2 points.
2. Live check in Instagram, Reddit and a browser with 3 words, scrolling.

**Done when:** the phone results match the twin and the live check passes.

### Acceptance contract: Phase 7.2 (includes the Chapter 7 gate)

| ID | Criterion | Pass threshold | How verified |
| --- | --- | --- | --- |
| AC-7.2-01 | Frozen benchmark | 100 unseen concrete words, ≥ 30 positives each, hash recorded before tuning | Manifest |
| AC-7.2-02 | Chapter 7 gate | ≥ 90% of benchmark words reach recall ≥ 90% at clean false-cover ≤ 5% (Balanced) | Report |
| AC-7.2-03 | No per-word tuning | No word-specific parameter anywhere | Code review + grep |
| AC-7.2-04 | Phone matches twin | Replay results within 2 points of the twin for 10 words | Replay |
| AC-7.2-05 | Live | 3 named words covered while scrolling Instagram, Reddit and a browser | Recording |

**If the gate is missed:** report the share of words that pass and the failure classes, then choose between (a) enabling the YOLOE Finder as a second opinion for small objects, (b) a larger image model on the phone, or (c) narrowing the promise to the word classes that pass.

# Appendices

## A. Gates and fallbacks at a glance

Each gate below is checked as part of the acceptance contract of that chapter's last phase (1.3, 2.3, 3.3, 4.3, 5.3, 6.3).

| Gate | Passes if (target) | If it fails |
| --- | --- | --- |
| Ch 1 SEE | ≥ 90% of cats covered; < 5% of clean screenshots wrongly covered | Fixed 80-class detector + whole-post matching |
| Ch 2 MOTION | Covered within 0.3 s (p95); no flicker; < 1 wrong cover/min; < 15% of frames analysed | Solid covers, longer holds, more looks per second |
| Ch 3 SPEED | All on AI chip; look < 45 ms p95; < 3 GB; accuracy within 2 points | LiteRT runtime; drop the object finder; smaller models |
| Ch 4 PLUMBING | Small frames on change only; box drift < 8 px; permission flows handled; self-capture mitigated | Accessibility screenshot capture (~3 per second) |
| Ch 5 GUARD | Live cover < 0.3 s p95; no stutter; < 3 GB; ≤ 15% extra battery | Light defaults, smaller models, fewer looks |
| Ch 6 PRODUCT | Unaided setup by a new user; 3 clean demo runs | Cut scope to cats + one pack; rely on backup video |

## B. Open decisions

Decide these as early as possible; record answers in `docs/decisions.md`.

1. Main capture path for the demo: screen capture with the permission shortcut, or accessibility screenshots only? (Decide after 4.1.1 and 4.1.3.)
2. Skip list meaning: assumed to mean "apps Veil ignores".
3. Layer 1 peeking: assumed never allowed.
4. Protected video: do nothing, or cover the whole video while a concept is active?
5. Commercial plans: if yes, replace AGPL and research-only parts before release (Appendix C).
6. Languages: concept prompts are English-only for now; is Hindi or Hinglish needed?
7. Runtime: ONNX Runtime + QNN vs LiteRT (decided at the Chapter 3 gate).

## C. Licences to resolve before any commercial release

| Part | Licence (as found) | Impact |
| --- | --- | --- |
| SigLIP2 | Apache-2.0 | Fine |
| YOLOE (Ultralytics) | AGPL-3.0 (assumed from Ultralytics' other code; verify) | Commercial use needs an Ultralytics licence or a replacement |
| MobileCLIP / MobileCLIP2 weights (incl. YOLOE-26's text encoder) | Apple research-only | Not usable in a commercial product |
| NudeNet | AGPL-3.0 (reported; verify) | Needs replacement or compliance |
| Toxicity model (mmBERT-small based) | Apache-2.0 | Fine |

## D. Known technical notes and sources

- SigLIP2-B/16 on Snapdragon 8 Elite Gen 5: [Qualcomm AI Hub model page](https://huggingface.co/qualcomm/SigLIP2)
- YOLOv8 detection on Snapdragon: [Qualcomm AI Hub model page](https://huggingface.co/qualcomm/YOLOv8-Detection)
- YOLOE and its export behaviour: [Ultralytics YOLOE docs](https://docs.ultralytics.com/models/yoloe/)
- ONNX Runtime QNN provider: [docs](https://onnxruntime.ai/docs/execution-providers/QNN-ExecutionProvider.html). Reported setup issue on this chip generation and fixes: [issue #31353](https://github.com/microsoft/onnxruntime/issues/31353), [fix notes](https://github.com/itsallgoody/onnxruntime-qnn-snapdragon-8-elite-gen5)
- LiteRT on Qualcomm NPUs: [Google docs](https://developers.google.com/edge/litert/next/qualcomm)
- Android screen capture rules: [MediaProjection guide](https://developer.android.com/media/grow/media-projection), [Android 15 behaviour changes](https://developer.android.com/about/versions/15/behavior-changes-all)
- Foreground service types: [Android docs](https://developer.android.com/develop/background-work/services/fgs/service-types)
- Accessibility service API: [Android reference](https://developer.android.com/reference/android/accessibilityservice/AccessibilityService)
- Restricted settings for sideloaded apps: [Google help](https://support.google.com/android/answer/12623953)
- Play policy for accessibility use: [Google Play help](https://support.google.com/googleplay/android-developer/answer/10964491)
- Pigeon (Flutter ↔ Android bridge): [pub.dev](https://pub.dev/packages/pigeon)
- Tracking approach (two-pass matching): [ByteTrack paper](https://arxiv.org/abs/2110.06864)

**Still to verify on the real phone:**
- whether the capture-permission shortcut works on the iQOO's Android build;
- whether per-window screenshots (for peeking) are available and their rate limit;
- DRM behaviour per app;
- real battery cost.
