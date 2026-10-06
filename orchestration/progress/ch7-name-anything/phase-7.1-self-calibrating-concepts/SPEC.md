# SPEC · Phase 7.1 Self-calibrating concepts
MODEL: claude-opus-5-5 · Status: READY · PLAN.md lines 2146-2209 (Chapter 7 intro, 7.1.1-7.1.3, proof test, AC-7.1-01..05)
Waves: ONE wave, 7.1.1 / 7.1.2 / 7.1.3 in parallel. Then the orchestrator runs `tools/heavy/7.1-heavy.ps1 -Mini`, then the full run, alone.

## 1. Deviations and risks
- **Contract change (needs a waiver, W-7.1-card).** `compiled-concept.schema.json` uses `additionalProperties:false`. We add one OPTIONAL `auto` object, and `concept.schema.json` gets an optional `alsoHide`. contractVersion stays "1.0". Old cards stay valid, and old cards take the old Judge path byte for byte, so the golden tapes do not change.
- **The 53.3% was on the synthetic dev set** (1.2's drawn shapes, variant A; see data/ch1/results-synthetic.json). The public dev set showed 95%. AC-7.1-03 is judged on the synthetic dev set, variant A, as in Chapter 1. The public set is out (its dev embeddings are not cached).
- **Bank source: COCO 2017 train,** licence ids {4 CC BY 2.0, 5 CC BY-SA 2.0, 7 No known copyright, 8 US Gov} only, plus 1,500 generated UI/text screens (CC0, made by Veil) for "screenshots/text-heavy". Open Images originals are too large to stream. COCO has few memes; this is noted.
- **Labels come from COCO captions** (5 per image), mapped to vocab nouns. They drive exclusion and the recall positives. Captions miss some objects; the 99.5% quantile tolerates a few unlabelled positives.
- **The Kotlin port of the 7.1.2 rule is built in 7.1.3** ("the app side"), so the three builders have disjoint paths. The parity fixture comes from 7.1.2, which generates it first.
- **The Console still uses FakeGuard.** PigeonGuard.previewWord returns empty chips; real chips over Pigeon are DEFERRED (D-7.1-pigeon).
- **On the auto path, `calibrationOffset` and `userOffset` are ignored** (this is documented in judge.py and Judge.kt).
- **Risk: domain shift** (bank = photos, runtime = screenshot tiles). The 99.5% quantile assumes about 10 independent pieces per screen. If AC-03 fails, change only the GLOBAL Q table (never per word), record OVERRUN, and defer.
- **Heavy times:** the full bank is about 30k downloads (~4.8 GB streamed, none kept) plus ONNX CPU embedding plus 25k text encodes, so 60-120 min. It is resumable. Only one model process at a time.
- **No per-word tuning anywhere.** Every constant below is global.

## 2. Shared interfaces (verbatim)
**Global constants** (Python `workshop/twin/autocal.py`, and Kotlin `com.veil.teacher.autocal.AutoCal`):
```
TEMPLATES = ["a photo of a {w}", "a {w}", "a close-up of a {w}", "a {w} in a meme", "a drawing of a {w}"]   # {w} = singular(word) (existing rule)
Q_PER_MILLE = {light: 999, balanced: 995, strict: 980}   # balanced: 5% screen false-cover / ~10 pieces = 0.5% per piece
K_COMPETITORS = 8 ; N_CHIPS = 6 ; AUTO_MARGIN = 0.0 ; AUTO_NEAR_BAND = 0.02 ; IGNORE = teacher.IGNORE (3 phrases)
```
**Ensemble:** e_w = l2(mean_k l2(text(TEMPLATES[k] with w))). All dots are float64 on unit vectors.
**Quantile, integers only:** sort the null scores d ascending; n = len(d); k = (Qm*n + 999) // 1000 - 1, clamped to [0, n-1]; thr = d[k].

**Files.** Everything is little-endian. Dirs are `data/bank/{smoke,mini,v1}/` (git-ignored); the src cache is `data/bank/src/`.
```
bank.bin   "VBNK" u32 ver=1 | u32 n | u32 dim | u32 nLab | f32[n] scale | i8[n*dim] q | u32[n+1] labOff | u16[nLab] labIdx
vocab.bin  "VVOC" u32 ver=1 | u32 n | u32 dim | f32[n] scale | i8[n*dim] q | f32[n*3] thr (light,balanced,strict)
quantise:  v unit f32 -> scale = max|v|/127 ; q = clip(rint(v/scale), -127, 127)
dequant:   row = l2(float64(q) * scale)
vocab.json {"version":1,"bankId":"<sha256(bank.bin)[:16]>","dim":768,"templates":TEMPLATES,"ignore":IGNORE,
            "quantilesPerMille":{...},"k":8,"chips":6,"margin":0.0,
            "entries":[{"name":"buffalo","kind":"noun"|"ignore","forms":["buffalo","buffaloes"],"excl":[i..],"rel":[i..],"nPos":12}]}
items.jsonl one per bank row: {"row":0,"source":"coco"|"ui","id":"000000391895","url":"...","licenseId":4,"license":"CC BY 2.0","labels":[i..]}
```
- Vocab index = position in `entries`; the 3 ignore entries come last (excl = rel = []). `excl(v)` = {v} ∪ WordNet synonyms ∪ hyponyms (within vocab); `rel(v)` = excl ∪ hypernyms. Vocab thresholds use the DEQUANTISED vocab row, excluding bank rows whose labels hit `excl(v)`.

**Python `workshop/twin/bank/bankio.py`** (7.1.1 writes it FIRST, under 5 min; 7.1.2 imports it):
```python
@dataclass
class Bank: rows: np.ndarray; lab_off: np.ndarray; lab_idx: np.ndarray; bank_id: str
@dataclass
class Vocab: rows: np.ndarray; thr: np.ndarray; meta: dict      # rows float64 unit (n,dim); thr float32 (n,3)
def quantise(v: np.ndarray) -> tuple[np.ndarray, np.ndarray]     # (int8 (n,dim), f32 scale (n,))
def write_bank(path: Path, vecs: np.ndarray, labels: list[list[int]]) -> str   # returns bankId
def read_bank(path: Path) -> Bank
def write_vocab(folder: Path, vecs: np.ndarray, thr: np.ndarray, meta: dict) -> None
def read_vocab(folder: Path) -> Vocab
def excluded_rows(bank: Bank, excl: set[int]) -> np.ndarray     # bool mask, True = drop
```
**Word resolution** (the same on both sides):
- `lookup(word)` = the entry whose `forms` contain lower(collapse(word)) or singular(...), else None (OOV). In-vocab: stored row, thresholds, `excl`, `rel`. OOV: encode the ensemble; excl = {}; rel = {entries whose name == singular(word)}.

**Competitors:**
- Noun entries not in rel(w) and not positives, ranked by cos(e_w, e_v) descending (ties: lower index); keep the top K = 8; chips = the first 6 names. The 3 ignore entries are always appended as competitors (never chips).

**`auto` object** (optional in CompiledConcept; the cc's `thresholds` and `margin` mirror positives[0] and margin):
```json
"auto": {"rule":"null-quantile-v1","bankId":"..","margin":0.0,"excluded":12,"chips":["bison","yak","ox","cow","horse","deer"],
  "positives":[{"term":"buffalo","embedding":{Embedding v1.0},"thresholds":{"light":0.0,"balanced":0.0,"strict":0.0}}],
  "competitors":[{"term":"cow","embedding":{Embedding v1.0},"thresholds":{"balanced":0.0}}]}
```
- The Concept card gets an optional `"alsoHide": [string ≤64]` (at most 16). Selected chips become extra positives (stored vocab rows and thresholds); unselected chips stay competitors.

**Judge auto path** (twin `judge.py` and Kotlin `Judge.kt`; this branch is taken ONLY when cc has `auto`):
```
s_t = v·e_t ; comp = max_c (s_c - c.balanced)  (no competitors: -1e9)
hide_t = s_t >= t.thr[mode] and (s_t - t.thr.balanced) - comp >= auto.margin ;  hide = any(hide_t) or example rule (unchanged)
t* = argmax_t (s_t - t.thr[mode]) ; score = s_t* ; margin = max_t(s_t - t.thr.balanced) - comp
pRaw = probability = 1/(1+exp(-100*(s_t* - t*.thr[mode]))) ; nearMiss if !hide and s_t* >= t*.thr[mode] - 0.02
```
**Kotlin** (brain `contract/Types.kt`, additive with defaults):
```kotlin
data class AutoTerm(val term: String, val embedding: Embedding, val thresholds: Map<String, Double>)
data class AutoRule(val positives: List<AutoTerm>, val competitors: List<AutoTerm>, val margin: Double, val chips: List<String>)
// CompiledConcept gains a last param: val auto: AutoRule? = null
```
**Parity fixture** (7.1.2 writes it, 7.1.3 reads it): `workshop/twin/tests/fixtures/autocal/`
- `bank.bin` (n=600, dim=32, seed 71), `vocab.bin` + `vocab.json` (30 nouns + 3 ignore), and `expected.json` = `{queries:[{word, vector:[32 f], thresholds{light,balanced,strict}, excluded, competitors, chips}], vocabThr:[[3]], judge:[...]}`, with 3 queries: in-vocab, OOV, and in-vocab with 2 chips selected.

## 3. Sub-phases

### 7.1.1 Reference bank (Python and heavy script) · Builder A
**Owned paths:**
- `workshop/twin/bank/` (`__init__.py`, `bankio.py`, `coco.py`, `ui_synth.py`, `vocab.py`, `build_bank.py`, `bank_check.py`, `tests/`)
- `workshop/twin/bank/manifest-v1.json` and `licences-v1.csv` (written by the heavy run)
- `tools/heavy/7.1-heavy.ps1`
- `tools/verify/7.1.1.ps1`
- `pyproject.toml` and `uv.lock` (`uv add nltk requests`)

**Steps:**
1. Write `bankio.py` exactly as in §2, plus a round-trip test.
2. Write `coco.py`:
   - Download `http://images.cocodataset.org/annotations/annotations_trainval2017.zip` once into `data/bank/src/`; extract only `captions_train2017.json`; delete the zip.
   - Keep images with licence ∈ {4,5,7,8} whose captions hit none of the blocklist words {nude, naked, lingerie, underwear, bikini, shirtless, topless}.
   - Sort by id, shuffle with `np.random.default_rng(71)`, and take the first N.
   - Fetch `http://images.cocodataset.org/train2017/{file_name}` in memory with 8 threads. Never write images to disk; never view them.
3. Write `ui_synth.py`:
   - Deterministic PIL 360×720 "app screens" (bars, `ImageFont.load_default()` text lines, buttons, avatar rectangles; no animals or objects; seed = index). Licence "CC0-1.0 (generated by Veil)".
4. Write `vocab.py`:
   - Data: the nltk wordnet corpus (into `data/bank/src/nltk`).
   - Candidates: caption tokens → `wn.morphy(tok,'n')`, counted over ALL train captions.
   - Keep a lemma whose first noun synset has, in its hypernym closure, one of organism.n.01, artifact.n.01, food.n.01, food.n.02 or natural_object.n.01, with count ≥ 2.
   - Take the top `--vocab-limit` (default 5000) by count. `forms` = the raw tokens that morphy maps to it.
   - Compute excl and rel as in §2.
   - Item labels = the vocab indices whose forms appear in that item's caption tokens.
   - Encode with `workshop.forge.siglip2.runtime.OnnxDescriber.embed_texts` (the 5 templates, the ensemble), then compute the vocab thresholds against the bank.
5. Write `build_bank.py --out DIR --limit N --ui U --vocab-limit V`:
   - Embed images with `OnnxDescriber.embed_images` (the exported model the phone uses).
   - Resumable: checkpoint every 256 rows to `DIR/partial.npz` + `items.jsonl` (skip done rows on restart) and log rows/s and ETA.
   - At the end, write bank.bin, vocab.bin, vocab.json and items.jsonl. For the `v1` dir, also write `manifest-v1.json` (n, dim, bankId, sha256s, source counts, licence counts, the onnx sha256) and `licences-v1.csv` (row,source,id,licenseId,license,url).
   - Sizes: full = 28,500 COCO + 1,500 UI + 5,000 vocab (bank.bin ≈ 23 MB ≤ 40 MB); mini = 1,900 + 100 + 1,000; smoke = 200 + 20 + 100.
6. Write `bank_check.py --bank DIR --sample S`:
   - Seeded sample (rng 7) of S rows: re-fetch or re-render, re-embed, compare with the dequantised rows. Print `BANK_CHECK min_cos=<x> n=<S>` (exit 1 if < 0.999); assert every item's licence is allowed and print `LICENCES ok=<n>/<n>` (AC-05).
7. Write `tools/heavy/7.1-heavy.ps1 [-Mini]`:
   - Runs in sequence, logging to `data/bank/heavy-<mini|v1>.log`: build_bank (mini or v1), then bank_check (sample 64), then `python -m workshop.twin.autocal_eval --bank <dir>` (from 7.1.2).
   - Skips steps whose outputs exist. Ends `HEAVY 7.1: PASS` or `FAIL`.

**Verify `tools/verify/7.1.1.ps1`:**
1. pytest `workshop/twin/bank/tests`: bankio round-trip (quantise cos ≥ 0.9999), ui_synth determinism, the licence/blocklist filter on a 5-image fake captions json, and the vocab excl/rel on a tiny hand list.
2. `build_bank --out data/bank/smoke --limit 200 --ui 20 --vocab-limit 100` (skipped if already done).
3. `bank_check --bank data/bank/smoke --sample 16`. 4. Ends `VERIFY 7.1.1: PASS`.

### 7.1.2 Auto threshold, competitors, ensembles (twin) · Builder B
**Owned paths:**
- `workshop/twin/autocal.py`, `workshop/twin/autocal_eval.py`, `workshop/twin/judge.py` (auto branch only)
- `workshop/twin/tests/test_autocal.py`, `workshop/twin/tests/fixtures/autocal/`
- `contracts/compiled-concept.schema.json`, `contracts/concept.schema.json` (optional fields only)
- `docs/reports/ch7-autocal.md` (written by the eval)
- `tools/verify/7.1.2.ps1`

**Steps:**
1. Write `make_fixture()` in `test_autocal.py` (or `fixtures/make.py`):
   - Random unit vectors and labels (seed 71) via `bankio.write_bank` / `write_vocab`; `expected.json` from the Python implementation, incl. `judge` verdicts for 5 fixed vectors. Write it EARLY so Builder C can start.
2. Write `autocal.py` with the §2 constants, plus:
   - `ensemble(enc, word)`, `null_thresholds(bank, q, excl) -> (dict, n_excluded)`, `lookup(vocab, word)`, `competitors(vocab, q, idx, word)`, and `compile_auto(word, enc, bank, vocab, also_hide=()) -> dict`.
   - `compile_auto` returns a valid CompiledConcept with `auto`. It reuses `teacher.concept_card`, `_embeddings` and the Embedding layout, and adds `alsoHide` to the card when chips are selected.
3. Add the auto branch to `judge.py` exactly as in §2. Old cards must not touch any new code.
4. Schemas: add the optional `auto` and `alsoHide` (strict sub-schemas). Existing `contracts/examples` must stay valid.
5. Write `autocal_eval.py --bank DIR [--set synthetic] [--words ...]`:
   - Words: snakes, buffalo, umbrella, pizza, motorcycle, giraffe, kite, broccoli, surfboard, clock.
   - Text encoder: OnnxDescriber. Pieces: `run.run_set(set, "dev", [w], variant="A", mode="balanced", ccs={w: cc}, piece_fn=run.describer_pieces(desc), encoder=desc, lane="describer")`, reusing the cached synthetic-dev-A embeddings.
   - Clean false-cover is computed as in `report._scores`.
   - Recall = the share of bank rows whose labels hit excl(w) (the held-out positives, full-image fingerprint as one piece) that the auto judge hides at Balanced. Report nPos; if nPos < 5, recall is "n/a".
   - Report compile_auto time per word; write `data/bank/eval-<dir>.json` and `docs/reports/ch7-autocal.md`; print `AUTOCAL snakes cleanFalseCover=<x>` (exit 1 if > 0.05).

**Verify `tools/verify/7.1.2.ps1`** (no model load):
1. pytest `test_autocal.py`:
   - The fixture regenerates identical to `expected.json`.
   - Quantile index cases: n = 600, 2000 and 30000 for each Qm.
   - Exclusion works, and in-vocab words use the stored thresholds.
   - The competitor order is right (rel and positives excluded; ignore entries appended).
   - Auto judge: the hide/nearMiss cases.
   - An old card through the judge equals its pre-change output (use `guard/brain/src/test/resources/judge-golden.json` or an existing golden).
   - Schema: an auto card is valid and the old examples are still valid.
2. Plus `workshop/twin/tests/test_twin_v0.py` and `test_motion.py`. 3. Ends `VERIFY 7.1.2: PASS`.

### 7.1.3 App side: Kotlin port and the "Also hide?" Console flow · Builder C
**Owned paths:**
- `guard/brain/src/main/kotlin/com/veil/brain/{contract/Types.kt,judge/Judge.kt}`
- `guard/teacher/src/main/kotlin/com/veil/teacher/autocal/` (`BankFile.kt`, `VocabFile.kt`, `AutoCal.kt`)
- `guard/teacher/src/test/kotlin/com/veil/teacher/AutoCalParityTest.kt`, `guard/teacher/build.gradle.kts` (test systemProperty `veil.repo`)
- `guard/app/src/main/java/com/veil/guard/wire/ml/ConceptPack.kt` (parse `auto`), `guard/app/src/test/java/com/veil/guard/wire/ml/ConceptPackTest.kt`
- `guard/app/src/main/java/com/veil/guard/teacher/TeacherDebugActivity.kt` (use compileAuto when `bank-v1.bin`, `vocab-v1.bin` and `vocab-v1.json` are in the ModelStore dir; else the old compile; log `ADD word=<w> ms=<t> chips=<..>`)
- `tools/phone/kit.ps1` (push the 3 bank files if present)
- `console/lib/guard/{guard_client.dart,fake_guard.dart,pigeon_guard.dart}`, `console/lib/screens/concept_studio_screen.dart`, `console/test/screens/also_hide_test.dart`
- `tools/verify/7.1.3.ps1`

**Steps:**
1. Kotlin types and Judge auto branch exactly as in §2. Old path untouched.
2. Write `BankFile` / `VocabFile`, which read the §2 binary format (`ByteBuffer` LITTLE_ENDIAN) and JSON (kotlinx).
3. Write `AutoCal`:
   - `fun compileAuto(word: String, alsoHide: List<String>, enc: TextEncoder?, bank: BankFile, vocab: VocabFile): Pair<CompiledConcept, List<String>>` (cc, chips).
   - `enc` is needed only for OOV words. Use the same arithmetic as Python: double dots, the integer quantile index.
   - The cc's `raw` map carries `auto` in the §2 JSON shape.
4. `AutoCalParityTest`:
   - Per fixture query: thresholds within 1e-4 of `expected.json`, same `excluded`, competitors and chips; recomputed vocabThr within 1e-4; the auto Judge on the `judge` vectors matches decisions and scores (1e-6).
   - If `data/bank/v1` (or `mini`) exists: load it and print `BANKLOAD n=<n> scanMs=<t>` for one 768-d scan (laptop proxy for AC-02).
5. Console:
   - `class WordPreview { final String word; final List<String> alsoHide; final List<String> preview; final int elapsedMs; }`; `GuardClient.previewWord(String text) → Future<WordPreview>`; `compileConcept(text, photos, {List<String> alsoHide = const []})`; `ConceptView` gains `alsoHide` (default const []).
   - FakeGuard: a fixed chip map `{buffalo:[bison,yak,ox,cow,horse,deer]}`, else 6 generic lookalikes `["<w> toy", ...]`. `preview` = 6 bank-caption strings. Unselected chips go into `butNot`.
   - PigeonGuard returns an empty WordPreview. Studio: typing a word shows "Also hide:" FilterChips plus a preview strip and "Active in N ms".
6. `also_hide_test.dart`: type "buffalo" → 6 chips → select "bison" → Add → the concept has alsoHide [bison], butNot contains "yak", and elapsedMs < 1000. Existing console tests stay green.

**Verify `tools/verify/7.1.3.ps1`:**
1. gradle-locked `:brain:test :teacher:test :app:testDebugUnitTest --tests *ConceptPackTest*` (includes GoldenTapesTest and GoldenTests: tapes stay exact). 2. `flutter test` in `console/`. 3. Ends `VERIFY 7.1.3: PASS`.

### Heavy (orchestrator, alone, after the 3 verifies pass)
- Run `tools\heavy\7.1-heavy.ps1 -Mini` (~10 min), then `tools\heavy\7.1-heavy.ps1` (full, 60-120 min, background, resumable).
- Commit `manifest-v1.json`, `licences-v1.csv` and `docs/reports/ch7-autocal.md` as `[7.1] reference bank v1`.
- If the full run cannot finish inside the session: AC-01 and AC-03 run on mini and are marked DEFERRED-full.

## 4. Acceptance contract
| ID | Criterion | Pass threshold (PLAN, verbatim) | How verified here |
| --- | --- | --- | --- |
| AC-7.1-01 | Bank faithful | Fingerprint cosine ≥ 0.999 against a fresh recomputation | bank_check (smoke 16 in 7.1.1; v1 64 in heavy) |
| AC-7.1-02 | Fast add | Word typed → concept active in ≤ 1 s on the phone | PENDING-HUMAN (ADD log line); JVM scanMs + FakeGuard proxy |
| AC-7.1-03 | Unseen word sane | "snakes" clean false-cover ≤ 5% (was 53%) | autocal_eval on synthetic dev A with the v1 bank |
| AC-7.1-04 | Parity kept | Golden tapes still match exactly; Kotlin and twin thresholds agree to 1e-4 | 7.1.2 + 7.1.3 verifies (GoldenTapesTest, AutoCalParityTest) |
| AC-7.1-05 | Licences | Every bank image has a recorded permissive licence | licences-v1.csv + bank_check `LICENCES ok=n/n` |

## 5. Proof test PT-7.1 "Buffalo"
- **Machine part:**
  - Run `autocal_eval` on v1 for the 10 unseen words. Every word reports recall (nPos) and clean false-cover; snakes is ≤ 5%.
  - `compile_auto("buffalo")` chips include at least one of {bison, ox, cow, yak}.
  - With `alsoHide=[]`, the auto judge on the bank's cow- and horse-labelled rows hides ≤ 5% of them (reported).
- **Human part (phone):**
  - Push the bank via kit.ps1 and add "buffalo" in TeacherDebugActivity. ADD ms ≤ 1000.
  - Buffalo posts in the Test Feed are covered; cow and horse posts are not, unless their chip is selected.

## 6. Human items
- **W-7.1-card:** approve the additive optional `auto` and `alsoHide` contract fields (v1.0 stays, old cards stay valid).
- **HC-7.1 (phone, PENDING-HUMAN, batch with HC-026):** the AC-02 timing and the PT "Buffalo" cover check above.
- **Licence note for review:** COCO images are kept only under CC BY 2.0, CC BY-SA 2.0, "No known copyright" or US Gov; the annotations are CC BY 4.0; WordNet uses the WordNet 3.0 licence. Attribution comes from licences-v1.csv.
