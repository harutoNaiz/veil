# Veil Test Feed

A tiny test app (`com.veil.testfeed`, label "Veil Test Feed") that stands in for a social-media feed. It shows
60 placeholder items in a scrolling list and writes down exactly what is on screen, so a later test can check
what the Guard sees against what really was there. It contains no real content: only coloured blocks with a
label, and a ruler.

## Items

Item `i` (0 to 59) has the id `item-%03d` and the kind `KINDS[i % 8]`, where
`KINDS = clean, cat, clean, spider, lookalike, clean, ruler, repost`.

- Height: 480 dp for `ruler` items, 320 dp for all others, plus an 8 dp gap below each item.
- Colour by kind: clean `#ECEFF1`, cat `#FFCC80`, spider `#B39DDB`, lookalike `#A5D6A7`, ruler white, repost `#FFCC80`.
- Label `#%03d <kind>` (a `repost` also says ` of item-001`). A `ruler` item draws a ruler instead of a label:
  a 1 px tick every 10 px, and a longer tick with the number every 100 px.
- Real cat, spider and Layer 1 images arrive with the phases that need them; this is version 1.

## Log file

`filesDir/feedlog.jsonl` (on the phone: `/data/data/com.veil.testfeed/files/feedlog.jsonl`). It is emptied each
time the app starts. Read it with `adb exec-out run-as com.veil.testfeed cat files/feedlog.jsonl` (debug build).
One JSON object per line. All times are milliseconds on the `SystemClock.uptimeMillis()` clock, which is the
same clock as the Guard's frame times. All positions are screen pixels. A `rect` is `{x, y, w, h}` and is not
clipped to the screen, so `y` can be negative.

| Line | Written when | Fields |
| --- | --- | --- |
| `session` | once, after the first layout | `v` (1), `tMs`, `screenWidthPx`, `screenHeightPx`, `densityDpi`, `viewport` (the feed area), `items` (each `itemId`, `kind`, `contentY`, `h`, with `contentY` counted from the top of the scroll content) |
| `frame` | each display frame in which the scroll position changed, and the first frame | `tMs`, `scrollY`, `visible` (each `itemId`, `kind`, `rect`) |
| `tap` | a finger lifts after a short press that did not move | `tMs`, `x`, `y`, `itemId` (left out when the tap misses every item) |
| `pause` | the app leaves the foreground | `tMs` |

Examples:

```json
{"type":"session","v":1,"tMs":1000000,"screenWidthPx":1440,"screenHeightPx":3168,"densityDpi":510,"viewport":{"x":0,"y":96,"w":1440,"h":2976},"items":[{"itemId":"item-000","kind":"clean","contentY":0,"h":1020}]}
{"type":"frame","tMs":1002000,"scrollY":0,"visible":[{"itemId":"item-000","kind":"clean","rect":{"x":0,"y":96,"w":1440,"h":1020}}]}
{"type":"tap","tMs":1003000,"x":720,"y":1200,"itemId":"item-000"}
{"type":"pause","tMs":1004000}
```

The log is flushed every 500 ms and when the app pauses. Logcat tag `VeilFeed` prints
`VEIL_FEED session items=60` at start.

## Build and test

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\with-env.ps1 --cd guard .\gradlew.bat --no-daemon :testfeed:assembleDebug :testfeed:testDebugUnitTest
```

The APK is `guard/testfeed/build/outputs/apk/debug/testfeed-debug.apk`. The code that decides what is visible
(`FeedGeometry`) and the log line builders (`FeedJson`) are plain Kotlin with JVM unit tests. On the Python
side, `workshop/bench/testfeed.py` reads the log and `workshop/bench/drive.py` scrolls the feed.
