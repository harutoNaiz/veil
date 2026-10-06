# Phase 7.1 Self-calibrating concepts · BUILT (full 30k bank done; phone checks pending)
Commits: 0ce0c2c (7.1.1 bank), f863bf2 (7.1.2 twin autocal), 7310cb2 (7.1.3 Kotlin + chips), 61297ee (fix1: GPU via DirectML), 7bb68b1 (A1 null-quantile-v2), 48e18a9 (relabel header fix), 10f61e4 (eval report), 16ca97e (text encoder on DML), 958b0d3 (full v1 bank report)

## What it does
Type any concrete word, and the phone scores it against a bundled bank of safe image fingerprints, then sets its own threshold from the "null" score distribution. There is no per-word tuning. It adds competitor lookalike words, a prompt ensemble, and "Also hide?" chips.

## Key results (mini GPU bank, 2,000 rows, synthetic dev A)
- **AC-7.1-03 PASS:** "snakes" clean false-cover went from 0.533 (hand-tuned baseline) to 0.933 (v1 auto rule) to **0.000** (v2).
- All 12 eval words: clean false-cover 0.0. Cats and spiders keep screen recall 1.0.
- **Warning for 7.2:** bank recall on held-out positives is low for some words: motorcycle 0.67, broccoli 0.62, pizza 0.94, kite 0.93.

## Full bank v1 (2026-10-07, new machine, RTX 4050 DML): HEAVY 7.1 PASS
- bankId 2f82a5e9b31fda91, n=30000 (28500 COCO + 1500 UI), vocab 4583, bank_check min_cos 0.99937. Build 24 min (vocab text encode now on DML: 171 vs 2.3 texts/s on CPU).
- **AC-7.1-03 PASS on v1:** clean false-cover 0.0 for all 12 words (snakes thr 0.0451). Screen recall cats/spiders 1.0.
- Bank recall (held-out positives): kite 0.96, pizza 0.95, surfboard 0.94, giraffe 0.93, clock 0.92, cats 0.90, umbrella 0.88, broccoli 0.67, motorcycle 0.62, **buffalo 0.33 (n=12), snakes 0.14 (n=14)**. Rare words recall poorly; 7.2 measures it properly.

## Repairs
- **v1 failure, a domain offset:** all text vectors share the direction ē, and synthetic tiles project onto it about 5× more than photos. Fix: score along l2(e − ē), a global rule (A1).
- **Vocab bug:** only the first WordNet synset was checked, so "kite" was OOV. Now any synset counts.
- **relabel_bank** wrote nLabels into the dim header field. Fixed, with a regression test.

## GPU
torch and onnxruntime in the lock are CPU-only. The bank build uses `uv run --locked --with onnxruntime-directml` (GTX 1650 Ti): 45 img/s for the model; about 5 img/s end to end, bounded by downloads and preprocessing.

## Pending
- (done) full 30k bank data/bank/v1.
- HC-028: waiver review, plus "buffalo" on the phone in ≤ 1 s.
