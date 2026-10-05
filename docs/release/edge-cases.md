# Edge-case checklist (phone)

| Case | Steps | Expected | Pass/Fail | Date |
|---|---|---|---|---|
| Rotation | Rotate the phone while a cover is up | Cover follows rotation, no flash |  |  |
| Split screen | Open a feed in split screen | Cover fits its pane |  |  |
| Keyboard open | Open the keyboard in a chat | Cover not hidden by keyboard |  |  |
| Picture-in-picture | Start PiP video, scroll a feed | Cover shown over PiP content |  |  |
| Notification shade | Pull the shade down over a cover | Cover stays, or re-covers on close |  |  |
| App switch mid-scroll | Switch apps mid-scroll | Cover gone within 2 s, no stuck cover |  |  |
| Blind app (Netflix) | Open Netflix | Known limit: protected video is not seen (see known-issues) |  |  |
| 20-minute heat run | Run Veil 20 min; run `adb shell dumpsys thermalservice` before and after | No crash; thermal status not worse than moderate |  |  |
