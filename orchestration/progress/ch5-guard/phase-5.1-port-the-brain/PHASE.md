# Phase 5.1 Port the brain · WAITING_HUMAN (phone)
Commits: 62a0ffa (5.1.1), b22bc1c (5.1.2), 391fb4e (5.1.3) · Spec: SPEC.md (121 lines)

## Summary
The Guard's decision logic now exists in plain Kotlin (`guard/brain`, no Android dependencies):
- change detector, scheduler and Gatekeeper;
- tracker and planner;
- cache and Judge.

It reproduces all 3 golden tapes **exactly** on the laptop JVM. A CI workflow runs the tapes on every change. The cache and Judge are checked against Python-generated reference files (`workshop/brain_ref/`), because the tapes contain no cache or Judge records.

The Teacher (`guard/teacher`) builds concept cards that match Python exactly (sha256), with prompt cosine ≥ 0.99. Laptop timing is about 1.5-2 s per card (informational; the phone target is ≤ 1 s). The store is AES-GCM encrypted.

## Acceptance criteria
| AC | Result |
| --- | --- |
| AC-5.1-01 tapes exact | PASS on the JVM · on-phone run PENDING (phone) |
| AC-5.1-02 Judge matches | PASS (reference fixtures) |
| AC-5.1-03 portable | PASS (no Android in `:brain`) |
| AC-5.1-04 Teacher ≤ 1 s | PENDING (phone) |
| AC-5.1-05 Teacher matches | PASS (cosine ≥ 0.99, cards identical) |
| AC-5.1-06 stored safely | unit tests PASS · restart / unreadable-without-key check PENDING (phone) |
| AC-5.1-07 live changes ≤ 1 s | PENDING (phone) |

## Deferred / notes
- **Deferred:**
  - the SigLIP2 tokenizer on the phone (TeacherDebugActivity builds the card only);
  - the object finder's text encoder (accepted deviation in 3.1);
  - bit-exact phash on the phone.
- **Note:** `params.json` is copied into the androidTest assets, so it can drift from `workshop/twin/params.json`. Keep them in sync.
