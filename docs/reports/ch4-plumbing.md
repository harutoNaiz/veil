
## Phase 4.1 Screen capture

Source: SPEC 4.1 (4.1.3 part: backup path, blind spots). Status: machine checks done; every device row is PENDING-HUMAN.

### Behaviour table (AC-4.1-06)

| Situation | Expected | Observed |
| --- | --- | --- |
| Lock then unlock (Android 15 QPR1+) | projection stops, state awaitingPermission (reason keyguard), Resume Veil needs a new consent | PENDING-HUMAN |
| Status-bar capture chip tap | outcome recorded | PENDING-HUMAN |
| App killed (force-stop) | awaitingPermission within 1 s of restart or Resume Veil; new consent | PENDING-HUMAN |
| `appops set com.veil.guard PROJECT_MEDIA allow` | dialog skipped? survives lock? | PENDING-HUMAN |
| Pause / resume x10 | no consent dialog | PENDING-HUMAN |
| Backup (accessibility screenshot) source on | >= 2 fps, switched with no restart; needs 4.2 wiring | PENDING-HUMAN |

### Compatibility table (AC-4.1-08)

Blind = frames are black. Test accounts only.

| App | Package | Black frames? | Blind rect reported? |
| --- | --- | --- | --- |
| Netflix | com.netflix.mediaclient | PENDING-HUMAN | PENDING-HUMAN |
| Prime Video | com.amazon.avod.thirdpartyclient | PENDING-HUMAN | PENDING-HUMAN |
| Chrome Incognito | com.android.chrome | PENDING-HUMAN | PENDING-HUMAN |
| A banking app | (test app) | PENDING-HUMAN | PENDING-HUMAN |
| Instagram DMs | com.instagram.android | PENDING-HUMAN | PENDING-HUMAN |
| YouTube | com.google.android.youtube | PENDING-HUMAN | PENDING-HUMAN |
| WhatsApp | com.whatsapp | PENDING-HUMAN | PENDING-HUMAN |
| Test Feed | com.veil.testfeed | PENDING-HUMAN | PENDING-HUMAN |

## Phase 4.3 Drawing covers

Source: SPEC 4.3. Status: machine checks done (renderer, own-cover registry, long-press detector, touch replay, join script); every device row is PENDING-HUMAN. Per amendment A1 only one production accessibility service exists; the overlay is hosted by the Guard service, and `SelfCapture.install(service)` is the hook to call from it.

| AC | Result |
| --- | --- |
| AC-4.3-04 Self-capture settled | PENDING-HUMAN: run `tools\phone\4.3.3-phone.ps1`, `selfcap_check.py` prints "covers captured: yes/no"; add 2 example frames here. Mitigation if yes: ownOverlay from `own_join.py` (done); if the join is unreliable, ownOverlay = "unknown". |
| AC-4.3-05 Own covers reported | Pytest/JVM pass (join by tMs, outward rounding within 2 px). Device join PENDING-HUMAN. |
| AC-4.3-06 Peek known | PENDING-HUMAN: `peekprobe` writes `peek.jsonl` (successes, error codes, min interval); API 34+ only, otherwise "unavailable". |
| AC-4.3-07 Long-press | JVM pass (tap, drag, 500 ms hold, cancel). Device gestures log PENDING-HUMAN. |

Peek rate: PENDING-HUMAN. Drift table: `veil/data/ch4/drift.md` (4.3.2, PENDING-HUMAN).

## Chapter 4 gate

Decision: PENDING-HUMAN. Build and machine checks for 4.1, 4.2 and 4.3 are in place; the gate is signed after the device rows (AC-4.1 capture, AC-4.2 scrolling, AC-4.3-01 to 07) are read on the phone. If rejected: "Apply the Chapter 4 fallback, and if self-capture cannot be handled, switch to solid covers with longer holds (as in the Chapter 2 fallback)."

Signed: ______
