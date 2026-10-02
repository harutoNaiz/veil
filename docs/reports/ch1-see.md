# Chapter 1 SEE prototype report (synthetic)

Set: **synthetic**, 1.2's synthetic drawn shapes: pipeline check only, the numbers mean little. Generated 2026-10-02T08:25:11Z.

> Numbers here are NOT the Chapter 1 gate. The real gate (AC-1.3-01/02/03) is PENDING-HUMAN.

| Set | Role | Balanced cats recall | Balanced clean false-cover (cats) |
| --- | --- | --- | --- |
| public | public sample, not the frozen real test set (indicative baseline) | 100.0% | 5.0% |
| synthetic | 1.2's synthetic drawn shapes: pipeline check only, the numbers mean little | 100.0% | 0.0% |
| real | the frozen real labelled set (the gate set) | PENDING-HUMAN | PENDING-HUMAN |

## Score table

Dev split, calibrated thresholds, per mode (recall / precision / clean false-cover).

| Mode · concept | Recall | Precision | Clean false-cover |
| --- | --- | --- | --- |
| light · cats | 100.0% | 76.5% | 0.0% |
| light · spiders | 100.0% | 55.4% | 0.0% |
| balanced · cats | 100.0% | 76.5% | 0.0% |
| balanced · spiders | 100.0% | 55.4% | 0.0% |
| strict · cats | 100.0% | 64.8% | 0.0% |
| strict · spiders | 100.0% | 47.4% | 6.7% |

AC-1.3-04 ordering (Light <= Balanced <= Strict, recall and wrong covers): OK

Test split (Balanced only; each test run is logged, 3 allowed in total):

| Concept | Recall | Precision | Clean false-cover |
| --- | --- | --- | --- |
| cats | 96.0% | 71.2% | 0.0% |
| spiders | 100.0% | 54.9% | 10.0% |

## Variants

Chosen: **A**. A chosen: best mean recall at <=5% clean false-cover; A, C tied within 0.005, the faster one won (A: recall 1.000, 4.23 s/screen, B: recall 0.273, 0.16 s/screen (over 5% false-cover), C: recall 1.000, 4.49 s/screen)

| Variant | Concept | Recall | Precision | Clean false-cover | t | Sec/screen | Note |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | cats | 100.0% | 78.7% | 0.0% | 0.85 | 4.23 |  |
| A | spiders | 100.0% | 81.2% | 0.0% | 0.95 | 4.23 |  |
| B | cats | 46.5% | 43.5% | 6.7% | 0.95 | 0.16 | no point at <=5% clean false-cover; lowest shown |
| B | spiders | 8.0% | 8.3% | 13.3% | 0.95 | 0.16 | no point at <=5% clean false-cover; lowest shown |
| C | cats | 100.0% | 83.7% | 0.0% | 0.85 | 4.49 |  |
| C | spiders | 100.0% | 85.7% | 0.0% | 0.95 | 4.49 |  |

Speed is CPU torch and relative only (DV-1).

## Calibration and thresholds

| Concept | calibrationOffset | butNotExtra | exampleThreshold |
| --- | --- | --- | --- |
| cats | -0.477835 | none | None |
| spiders | -0.285157 | none | None |

Thresholds: Light 0.35, Balanced 0.35, Strict 0.25; margin 0.01.


## Examples gain

Centroid of dev cat crops; their screens are excluded from this measurement. Indicative only (DV-7).

Concept cats, 4 example crops (their screens excluded). Balanced recall on the remaining dev screens: 100.0% without, 100.0% with; gain 0.0% (indicative). exampleThreshold 0.9. Kept: False.

## Unseen concept

Word **snakes** (never tuned): card valid = True, compiled card valid = True, end to end = True. Tuned global thresholds, calibrationOffset 0 (never calibrated).

Scores on dev with the shared thresholds and no per-word calibration (no pass/fail threshold): covers 133, clean false-cover 53.3%, recall n/a.

## List switch

Result: **PASS**. One Describer and one Finder, no reload, no re-export; weight files unchanged (sha256).

- sequence: cats -> spiders -> snakes -> bicycles
- sameInstances: True
- sameWeights: True
- finderTest: 1.3.2 test_finder list-switch PASS

## Successes (10)

| Image | Concept | Reason |
| --- | --- | --- |
| chrome-feed-0033.png | cats | covered (photo) |
| chrome-feed-0048.png | cats | covered (photo) |
| instagram-feed-0001-dup.png | cats | covered (emoji cat-emoji) |
| instagram-feed-0016.png | cats | covered (emoji cat-emoji) |
| instagram-feed-0061.png | cats | covered (photo) |
| whatsapp-feed-0019.png | cats | covered (photo) |
| whatsapp-feed-0064.png | cats | covered (photo) |
| x-feed-0035.png | cats | covered (photo) |
| youtube-feed-0017.png | cats | covered (photo) |
| youtube-feed-0037.png | spiders | covered (photo) |

## Failures (10)

| Image | Concept | Reason |
| --- | --- | --- |
| chrome-feed-0033.png | cats | cover not on any labelled cats |
| chrome-feed-0063.png | spiders | cover not on any labelled spiders |
| instagram-feed-0021.png | spiders | cover not on any labelled spiders |
| whatsapp-feed-0024.png | spiders | cover not on any labelled spiders |
| youtube-feed-0007.png | cats | cover not on any labelled cats |
| chrome-feed-0033.png | spiders | cover not on any labelled spiders |
| chrome-feed-0038.png | cats | cover not on any labelled cats |
| chrome-feed-0038.png | spiders | cover not on any labelled spiders |
| chrome-feed-0048.png | cats | cover not on any labelled cats |
| chrome-feed-0048.png | spiders | cover not on any labelled spiders |

The gallery stays in git-ignored `data/ch1/gallery/`; this report cites image names only.

## Chosen models

- Variant A; spaceIds: {"describer": "siglip2-base-p16-224", "finder": "yoloe-26s-mobileclip2-b"}
- torch 2.14.1 (CPU), transformers 5.18.0, ultralytics 8.4.171
- SigLIP2 HF commit 75de2d55ec2d0b4efc50b3e9ad70dba96a7b2fa2; YOLOE yoloe-26s-seg.pt sha256 48f24206bc8680d60cbbfa296b0140da849669b9515058b72f5a945142df0654
- Licence, SigLIP2: Apache-2.0
- Licence, YOLOE (Ultralytics): AGPL-3.0
- Licence, YOLOE text encoder (MobileCLIP family): Apple research-only (per D-001, verify)

## Gate

Gate: PENDING-HUMAN (real frozen test set); fallback rule per PLAN 1.3 'If rejected'.

AC-1.3-01, 02, 03 and the Chapter 1 gate need `tools\ch1_see.ps1 -Set real -Test` (HC-1.3-a).

