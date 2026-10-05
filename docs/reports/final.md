# Veil final evaluation

Build: ed55e66 | Date: 2026-10-05

## How to read

measured means the value came from a result file. PENDING-HUMAN means it is not
measured yet. Nothing here is estimated or carried forward from older runs.

## Phone

| id | claim | value | status | conditions | source |
| --- | --- | --- | --- | --- | --- |
| F-01 | time to cover p95 ms (phone) | — | PENDING-HUMAN | phone run | data/final/phone-metrics.json |
| F-31 | looks per second | — | PENDING-HUMAN | phone run | data/final/phone-metrics.json |
| F-32 | AI ms per look p95 | — | PENDING-HUMAN | phone run | data/final/phone-metrics.json |
| F-33 | memory MB peak | — | PENDING-HUMAN | phone run | data/final/phone-metrics.json |
| F-34 | battery % per hour (light) | — | PENDING-HUMAN | phone run | data/final/phone-metrics.json |
| F-02 | battery % per hour (balanced) | — | PENDING-HUMAN | phone run | data/final/phone-metrics.json |
| F-36 | battery % per hour (strict) | — | PENDING-HUMAN | phone run | data/final/phone-metrics.json |

## Chapter one: seeing

| id | claim | value | status | conditions | source |
| --- | --- | --- | --- | --- | --- |
| F-03 | cats recall | 1.00 | measured | public sample, not the frozen set; laptop, balanced mode | data/ch1/results-public.json |
| F-04 | cats clean false covers | 0.29 | measured | public sample, not the frozen set; laptop, balanced mode | data/ch1/results-public.json |
| F-05 | spiders recall | 1.00 | measured | public sample, not the frozen set; laptop, balanced mode | data/ch1/results-public.json |
| F-06 | spiders clean false covers | 0.00 | measured | public sample, not the frozen set; laptop, balanced mode | data/ch1/results-public.json |

## Chapter two: motion

| id | claim | value | status | conditions | source |
| --- | --- | --- | --- | --- | --- |
| F-07 | time to cover p95 ms (laptop replay) | — | PENDING-HUMAN | laptop replay of recorded sessions (synthetic test sessions), balanced mode | data/ch2/motion-eval/scores.json |
| F-08 | frames analysed % | 12.7 | measured | laptop replay of recorded sessions (synthetic test sessions), balanced mode | data/ch2/motion-eval/scores.json |
| F-09 | wrong covers per minute | 8.7 | measured | laptop replay of recorded sessions (synthetic test sessions), balanced mode | data/ch2/motion-eval/scores.json |

## Chapter three: on-device profile

| id | claim | value | status | conditions | source |
| --- | --- | --- | --- | --- | --- |
| F-10 | AI latency per model on the NPU | — | PENDING-HUMAN | profile table values are fixtures, not a phone run | docs/reports/ch3-profile.md |
| F-11 | NPU share per model | — | PENDING-HUMAN | profile table values are fixtures, not a phone run | docs/reports/ch3-profile.md |

## Packs

| id | claim | value | status | conditions | source |
| --- | --- | --- | --- | --- | --- |
| F-20 | alcohol recall | 1.00 | measured | hand-written text lines (image set PENDING-HUMAN); status PENDING-HUMAN | workshop/packs/reports/alcohol.json |
| F-21 | alcohol clean false covers | 0.00 | measured | hand-written text lines (image set PENDING-HUMAN); status PENDING-HUMAN | workshop/packs/reports/alcohol.json |
| F-22 | gore recall | 1.00 | measured | hand-written text lines (image set PENDING-HUMAN); status PENDING-HUMAN | workshop/packs/reports/gore.json |
| F-23 | gore clean false covers | 0.00 | measured | hand-written text lines (image set PENDING-HUMAN); status PENDING-HUMAN | workshop/packs/reports/gore.json |
| F-24 | needles recall | 1.00 | measured | hand-written text lines (image set PENDING-HUMAN); status PENDING-HUMAN | workshop/packs/reports/needles.json |
| F-25 | needles clean false covers | 0.04 | measured | hand-written text lines (image set PENDING-HUMAN); status PENDING-HUMAN | workshop/packs/reports/needles.json |
| F-26 | spiders recall | 0.88 | measured | public-photos (8 spider, 42 clean); status PASS | workshop/packs/reports/spiders.json |
| F-27 | spiders clean false covers | 0.00 | measured | public-photos (8 spider, 42 clean); status PASS | workshop/packs/reports/spiders.json |
| F-28 | spoiler-breaking-bad recall | 1.00 | measured | hand-written text lines (image set PENDING-HUMAN); status PENDING-HUMAN | workshop/packs/reports/spoiler-breaking-bad.json |
| F-29 | spoiler-breaking-bad clean false covers | 0.00 | measured | hand-written text lines (image set PENDING-HUMAN); status PENDING-HUMAN | workshop/packs/reports/spoiler-breaking-bad.json |

## Limits

- Protected video (for example Netflix) cannot be seen, so it is not covered.
- A short delay passes before a cover appears on new content.
- Laptop numbers are not phone numbers; only the Phone table is from the phone.
