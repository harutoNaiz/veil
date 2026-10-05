# Chapter 3 speed report (DRAFT)

Status: all phone numbers PENDING-PHONE. Scripts: `tools/phone/3.3/` (`pt.ps1` runs the whole sitting). Evidence goes to `data/ch3/phone/<stamp>/`.
Note: `budget.json` is still `"source": "fixture"`, so the 45 ms budget is not measured yet.

## Per-model latency (timing.csv, `TimingReportKt`)
| runtime | model | phase | n | p50 ms | p95 ms |
|---|---|---|---|---|---|
| ort-qnn | look (Balanced) | warm | PENDING-PHONE | PENDING-PHONE | PENDING-PHONE |
| litert-npu | look (Balanced) | warm | PENDING-PHONE | PENDING-PHONE | PENDING-PHONE |

Gate: look p95 <= 45 ms: PENDING-PHONE.

## Residency, restart, memory
| item | value |
|---|---|
| VEIL_READY after force-stop (ms) | PENDING-PHONE |
| Resident TOTAL PSS (MB) | PENDING-PHONE |
| Burst vs low-power, 1000 looks | PENDING-PHONE |

## Soak (10 min, 3 looks/s, `SoakCheckKt`)
| looks | errors | PSS growth % (<= 5) | p95 drift % (<= 20) | max thermal | result |
|---|---|---|---|---|---|
| PENDING-PHONE | PENDING-PHONE | PENDING-PHONE | PENDING-PHONE | PENDING-PHONE | PENDING-PHONE |

## Phone vs laptop parity (`FpParityKt`, min cosine >= 0.98)
PENDING-PHONE.

## Runtime decision
ORT+QNN proposed, pending the phone comparison with LiteRT-NPU (see D-3.3 in docs/decisions.md).
