
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
