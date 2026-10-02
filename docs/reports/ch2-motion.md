# Chapter 2: Motion

## Look budget (Phase 2.2)

Tuned on synthetic dev sessions: synth-dev-1, synth-dev-2. Real dev recordings: PENDING-HUMAN (HC-2.2).

| mode | tile_level | min gap ms | looks/min | % frames analysed | % within 200 ms | p95 ms | cut recall % | false cuts/min |
|---|---|---|---|---|---|---|---|---|
| light | 8 | 250 | 163.6 | 9.1 | 98.2 | 166 | 100 | 0.00 |
| balanced | 8 | 250 | 163.6 | 9.1 | 98.2 | 166 | 100 | 0.00 |
| strict | 8 | 250 | 247.7 | 13.8 | 100.0 | 100 | 100 | 0.00 |

Per situation (% frames analysed, chosen params):

| mode | feedScroll | reels | video | static | other |
|---|---|---|---|---|---|
| light | 10.7 | 11.4 | 6.7 | 13.2 | 2.0 |
| balanced | 10.7 | 11.4 | 6.7 | 13.2 | 2.0 |
| strict | 18.2 | 15.9 | 6.7 | 13.2 | 2.0 |

Scene cuts (Balanced): recall 100%, false cuts 0.00/min (AC-2.2-02).

![look budget](img/ch2-look-budget.png)

## Steady covers (Phase 2.3)

Synthetic test sessions (oracle detector, 100 ms latency, self-capture on).
Real recordings: PENDING-HUMAN (HC-2.3).

| mode | ttc median ms | ttc p95 ms | flicker | wrong/min | coverage % | glue px | frames analysed % | appearances | frames |
|---|---|---|---|---|---|---|---|---|---|
| light | 366 | 1000000000 | 0 | 8.736 | 76.42 | 2 | 12.61 | 162 | 1800 |
| balanced | 233 | 1000000000 | 0 | 8.736 | 82.76 | 2 | 12.67 | 162 | 1800 |
| strict | 100 | 1000000000 | 0 | 20.384 | 87.17 | 2 | 15.44 | 162 | 1800 |

Acceptance (Balanced):

- AC-2.3-01: FAIL (p95=1000000000ms)
- AC-2.3-02: PASS (flicker=synth-test-3:0,synth-test-4:0)
- AC-2.3-03: FAIL (8.736/min)
- AC-2.3-04: FAIL (82.76%)
- AC-2.3-05: PASS (2px)

Cache hit rate per situation (Balanced, near-duplicate crops from the truth):

| situation | hits | misses | hit % |
|---|---|---|---|
| feedScroll | 285 | 87 | 76.6 |
| reels | 7 | 24 | 22.6 |
| static | 100 | 35 | 74.1 |
| video | 0 | 0 | 0.0 |

PT-2.3 torture (torture-22, Balanced):

| mode | ttc median ms | ttc p95 ms | flicker | wrong/min | coverage % | glue px | frames analysed % | appearances | frames |
|---|---|---|---|---|---|---|---|---|---|
| light | 0 | 1000000000 | 1 | 30.769 | 88.09 | 2 | 10.97 | 30 | 720 |
| balanced | 0 | 1000000000 | 0 | 46.154 | 91.14 | 3 | 10.56 | 30 | 720 |
| strict | 0 | 1000000000 | 0 | 30.769 | 93.97 | 2 | 17.64 | 30 | 720 |

re-cover max 234 ms.

### Chapter 2 gate decision

GATE ch2 (synthetic): **FAIL** (real gate: PENDING-HUMAN).

PLAN fallback run (`--fallback`: solid only, holds x2, rates x2; report-only):

| mode | ttc median ms | ttc p95 ms | flicker | wrong/min | coverage % | glue px | frames analysed % | appearances | frames |
|---|---|---|---|---|---|---|---|---|---|
| balanced | 233 | 1000000000 | 0 | 20.384 | 83.13 | 2 | 16.06 | 162 | 1800 |

fallback GATE: FAIL

Deviations: DV-1 oracle detector (real detector DEFERRED); DV-2 synthetic gate; DV-3 cats (L2) + spiders (L1 stand-in); DV-4 confirm looks; DV-5 scene cut ends self-capture hold; DV-6 whole-post covers deferred; DV-7 64-bit DCT cache hash.

Videos: [feed](media/ch2-feed.mp4), [reels](media/ch2-reels.mp4), [video](media/ch2-video.mp4).
