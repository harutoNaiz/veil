# Phase 7.1 Self-calibrating concepts · BUILT (full 30k bank building; phone checks pending)
Commits: 0ce0c2c (7.1.1 bank), f863bf2 (7.1.2 twin autocal), 7310cb2 (7.1.3 Kotlin + chips), 61297ee (fix1: GPU via DirectML), 7bb68b1 (A1 null-quantile-v2), 48e18a9 (relabel header fix), 10f61e4 (eval report)

## What it does
Type any concrete word, and the phone scores it against a bundled bank of safe image fingerprints, then sets its own threshold from the "null" score distribution. There is no per-word tuning. It adds competitor lookalike words, a prompt ensemble, and "Also hide?" chips.

## Key results (mini GPU bank, 2,000 rows, synthetic dev A)
- **AC-7.1-03 PASS:** "snakes" clean false-cover went from 0.533 (hand-tuned baseline) to 0.933 (v1 auto rule) to **0.000** (v2).
- All 12 eval words: clean false-cover 0.0. Cats and spiders keep screen recall 1.0.
- **Warning for 7.2:** bank recall on held-out positives is low for some words: motorcycle 0.67, broccoli 0.62, pizza 0.94, kite 0.93.

## Repairs
- **v1 failure, a domain offset:** all text vectors share the direction ē, and synthetic tiles project onto it about 5× more than photos. Fix: score along l2(e − ē), a global rule (A1).
- **Vocab bug:** only the first WordNet synset was checked, so "kite" was OOV. Now any synset counts.
- **relabel_bank** wrote nLabels into the dim header field. Fixed, with a regression test.

## GPU
torch and onnxruntime in the lock are CPU-only. The bank build uses `uv run --locked --with onnxruntime-directml` (GTX 1650 Ti): 45 img/s for the model; about 5 img/s end to end, bounded by downloads and preprocessing.

## Pending
- The full 30k bank (data/bank/v1) is building.
- HC-028: waiver review, plus "buffalo" on the phone in ≤ 1 s.
