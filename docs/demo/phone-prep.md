# Phone prep (demo phone)

Only Veil's own packages and the Test Feed app are touched. No factory reset, no account changes, no other system settings than those listed here.

## Checklist
1. Install the sideloaded build: `adb install -r <demo-build>.apk` (build id: PENDING-HUMAN).
2. Grant permissions: the accessibility service, notifications and, if used, screen capture. Restricted settings for a sideloaded app may need allowing in the app info page.
3. Capture-permission shortcut: apply it only if it works on this phone (PENDING-HUMAN: untested on the iQOO).
4. Accounts: test accounts only, with known content (cats, one fox, spiders, ordinary posts). No personal accounts.
5. Brightness fixed at a set level; auto-brightness off. Do-not-disturb on. Stay-awake as the spec allows.
6. Console starts with an empty concept list; Balanced mode.
7. Battery above 80 percent and the phone on the same Wi-Fi state as the rehearsal, so airplane mode is the only change.

## scrcpy recording (one file per rehearsal)
```
scrcpy --record data/rehearsal/run1.mp4 --no-audio
scrcpy --record data/rehearsal/run2.mp4 --no-audio
scrcpy --record data/rehearsal/run3.mp4 --no-audio
scrcpy --record data/rehearsal/airplane.mp4 --no-audio
```
Recordings stay in `data/`, which git ignores. Never upload them.

## Backup video
Record the full 7-step demo once with scrcpy, copy it to the presentation laptop, and play it with the network off (see rehearsal-log.md).
