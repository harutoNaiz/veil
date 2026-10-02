"""2.2.3 Look budget: evaluate the Gatekeeper on labelled sessions, tune, write the report."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from workshop.labels.recordings import boxes_at
from workshop.twin import gatekeeper as gk

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "docs" / "reports" / "ch2-motion.md"
CHART = ROOT / "docs" / "reports" / "img" / "ch2-look-budget.png"
SECTION = "## Look budget (Phase 2.2)"
MODES = ("light", "balanced", "strict")
SITS = ("feedScroll", "reels", "video", "static", "other")


def ensure_dev_set(dir: str | Path = "data/ch2/synth-dev") -> Path:
    from workshop.recordings.synth_session import generate

    d = Path(dir)
    for sid, seed in (("synth-dev-1", 1), ("synth-dev-2", 2)):
        if not (d / f"{sid}.session.json").exists():
            generate(d, sid, seconds=40, seed=seed)
    return d


def _covers(rect: dict, box: dict, sw: int, sh: int) -> bool:
    x0, y0 = max(box["x"], 0), max(box["y"], 0)
    x1, y1 = min(box["x"] + box["w"], sw), min(box["y"] + box["h"], sh)
    area = max(0, x1 - x0) * max(0, y1 - y0)
    if area == 0:
        return False
    ix = max(0, min(x1, rect["x"] + rect["w"]) - max(x0, rect["x"]))
    iy = max(0, min(y1, rect["y"] + rect["h"]) - max(y0, rect["y"]))
    return ix * iy * 2 >= area


def _read_tape_in(tape_in: Path) -> tuple[dict, list[dict]]:
    header, events = {}, []
    for line in Path(tape_in).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r["kind"] == "header":
            header = r
        elif r["kind"] == "event":
            events.append(r["event"])
    return header, events


def _scenes(session_json: Path) -> dict[int, str] | None:
    s = json.loads(Path(session_json).read_text(encoding="utf-8"))
    p = Path(session_json).parent / f"{s['sessionId']}.truth.jsonl"
    if not p.exists():
        return None
    return {
        r["i"]: r["scene"]
        for r in (json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip())
    }


def evaluate(session_json, label, tape_in, mode, params=None, look_ms=0) -> dict:
    """Raw sums for one session; `derive` turns pooled sums into the metrics."""
    recs = gk.run_tape(tape_in, mode, params, look_ms)
    header, events = _read_tape_in(tape_in)
    sw, sh = header["screenWidth"], header["screenHeight"]
    looks = [r for r in recs if r["kind"] == "look"]
    changes = [r for r in recs if r["kind"] == "change"]
    yes = [r for r in looks if r["look"]]
    lat: list[int | None] = []
    for tr in label["tracks"]:
        for sp in tr["spans"]:
            found = None
            for r in yes:
                if r["tMs"] < sp["startMs"]:
                    continue
                if r["tMs"] > sp["endMs"]:
                    break
                box = [b for b in boxes_at(label, r["tMs"]) if b["key"] == tr["key"]]
                full = r["rect"]["w"] >= sw and r["rect"]["h"] >= sh
                if full or (box and _covers(r["rect"], box[0]["rect"], sw, sh)):
                    found = r["tMs"] - sp["startMs"]
                    break
            lat.append(found)
    # scene cuts: flagged frames <= 500 ms apart form one cut
    groups: list[list[tuple[int, int]]] = []
    last = None
    for r in changes:
        if r["sceneCut"]:
            if last is None or r["tMs"] - last > 500:
                groups.append([])
            groups[-1].append((r["tMs"], r["frameId"]))
            last = r["tMs"]
    flagged = [t for g in groups for t, _ in g]
    marks = label.get("marks", [])
    cuts = [m["tMs"] for m in marks if m["type"] == "sceneCut"]
    other = [m["tMs"] for m in marks if m["type"] in ("appSwitch", "lock", "unlock")]

    def near(t, ms):
        return any(m - 50 <= t <= m + 300 for m in ms)

    hit = sum(1 for m in cuts if any(m - 50 <= g <= m + 300 for g in flagged))
    scenes = _scenes(session_json)

    def real(f):  # truth says the picture really changed (extends DV-4; synthetic only)
        return scenes is not None and scenes.get(f) != scenes.get(max(0, f - 3))

    false = sum(
        1 for g in groups if not any(near(t, cuts) or near(t, other) or real(f) for t, f in g)
    )
    scroll_t = [e["tMs"] for e in events if e.get("type") == "scrolled"]
    sit: dict[str, list[int]] = {}
    for r in looks:
        if scenes is None:
            name = "all"
        else:
            sc = scenes.get(r["frameId"], "other")
            if sc in ("feed", "grid"):
                scrolling = any(abs(t - r["tMs"]) <= 300 for t in scroll_t)
                name = "feedScroll" if scrolling else "static"
            else:
                name = sc if sc in ("reels", "video") else "other"
        a = sit.setdefault(name, [0, 0])
        a[0] += 1
        a[1] += 1 if r["look"] else 0
    dur = (looks[-1]["tMs"] - looks[0]["tMs"]) if len(looks) > 1 else 0
    return {
        "frames": len(looks), "looks": len(yes), "durMs": dur, "lat": lat, "cuts": len(cuts),
        "cutsHit": hit, "falseCuts": false, "skipped": looks[-1]["x"]["skipped"] if looks else 0,
        "situations": sit,
    }  # fmt: skip


def merge(results: list[dict]) -> dict:
    m = {"frames": 0, "looks": 0, "durMs": 0, "lat": [], "cuts": 0, "cutsHit": 0,
         "falseCuts": 0, "skipped": 0, "situations": {}}  # fmt: skip
    for r in results:
        for k in ("frames", "looks", "durMs", "cuts", "cutsHit", "falseCuts", "skipped"):
            m[k] += r[k]
        m["lat"] += r["lat"]
        for k, (f, lk) in r["situations"].items():
            a = m["situations"].setdefault(k, [0, 0])
            a[0] += f
            a[1] += lk
    return m


def derive(m: dict) -> dict:
    lat = m["lat"]
    ok = [x for x in lat if x is not None]
    n = max(1, len(lat))
    minutes = max(1, m["durMs"]) / 60000
    p95 = None
    if lat:
        full = sorted(x if x is not None else 10**9 for x in lat)  # a miss counts as infinite
        p95 = full[min(len(full) - 1, (95 * len(full) + 99) // 100 - 1)]
    return {
        "frames": m["frames"], "looks": m["looks"],
        "looksPerMin": m["looks"] / minutes,
        "pctAnalysed": m["looks"] * 100 / max(1, m["frames"]),
        "spans": len(lat), "misses": len(lat) - len(ok),
        "pctWithin200": sum(1 for x in ok if x <= 200) * 100 / n,
        "p95Ms": p95,
        "cutRecall": (m["cutsHit"] * 100 / m["cuts"]) if m["cuts"] else 100.0,
        "falseCutsPerMin": m["falseCuts"] / minutes, "skipped": m["skipped"],
        "situations": {k: {"frames": f, "looks": lk, "pct": lk * 100 / max(1, f)}
                       for k, (f, lk) in m["situations"].items()},
    }  # fmt: skip


def _load_split(sessions: Path, split: str | None) -> set[str] | None:
    p = sessions / "split.json"
    if not split or not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    ids = d.get(split) if isinstance(d, dict) else None
    return set(ids) if ids else None


def prepare(sessions: Path, labels: Path, out: Path, split: str | None = None) -> list[tuple]:
    """tape-in once per session (player, no video output). Returns (session, label, tape_in)."""
    from workshop.replay.pipeline import DummyPipeline
    from workshop.replay.player import replay

    keep = _load_split(sessions, split)
    items = []
    for sj in sorted(sessions.glob("*.session.json")):
        sid = json.loads(sj.read_text(encoding="utf-8"))["sessionId"]
        lp = labels / f"{sid}.json"
        if (keep is not None and sid not in keep) or not lp.exists():
            continue
        tape = out / f"{sid}.tape-in.jsonl"
        if not tape.exists():
            replay(sj, DummyPipeline(), out, video=False)
        items.append((sj, json.loads(lp.read_text(encoding="utf-8")), tape))
    return items


def run_eval(items, mode, params=None) -> dict:
    return derive(merge([evaluate(sj, lab, ti, mode, params) for sj, lab, ti in items]))


def _params_with(raw: dict, mode: str, tile_level: int, gap: int) -> dict:
    p = copy.deepcopy(raw)
    p["modes"][mode]["change"]["tile_level"] = tile_level
    p["modes"][mode]["sched"]["min_immediate_gap_ms"] = gap
    return p


def cmd_eval(a) -> int:
    items = prepare(a.sessions, a.labels, a.out, a.split)
    if not items:
        print("no labelled sessions found")
        return 2
    raw = json.loads(gk.PARAMS.read_text(encoding="utf-8"))
    r = run_eval(items, "balanced", raw)
    c2 = r["cutRecall"] >= 90 and r["falseCutsPerMin"] <= 1
    c5 = r["pctAnalysed"] < 15
    c6 = r["pctWithin200"] >= 95
    print(
        f"AC-2.2-02: {'PASS' if c2 else 'FAIL'} recall {r['cutRecall']:.0f}% "
        f"false {r['falseCutsPerMin']:.2f}/min"
    )
    v5 = f"{r['pctAnalysed']:.1f}% frames analysed"
    print(f"AC-2.2-05: {'PASS' if c5 else ('WAIVER-PROPOSED' if c6 else 'FAIL')} {v5}")
    print(f"AC-2.2-06: {'PASS' if c6 else 'FAIL'} {r['pctWithin200']:.1f}% within 200 ms")
    (a.out / "eval.json").write_text(json.dumps(r, indent=1), encoding="utf-8")
    return 0


def cmd_tune(a) -> int:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    items = prepare(a.sessions, a.labels, a.out, a.split)
    raw = json.loads(gk.PARAMS.read_text(encoding="utf-8")) if gk.PARAMS.exists() else None
    raw = raw or gk.default_raw()
    for m in MODES:
        raw["modes"][m]["change"]["cut_tile_level"] = a.cut_tile_level
    grid = [(t, g) for t in (8, 12, 16, 24) for g in (100, 150, 200, 250)]
    pts: dict[str, list[tuple]] = {}
    chosen: dict[str, tuple] = {}
    for mode in MODES:
        pts[mode] = []
        for tl, gap in grid:
            r = run_eval(items, mode, _params_with(raw, mode, tl, gap))
            pts[mode].append((tl, gap, r))
        good = [x for x in pts[mode] if x[2]["pctWithin200"] >= 95]
        if good:
            best = min(good, key=lambda x: (x[2]["pctAnalysed"], x[0], x[1]))
        else:
            best = max(pts[mode], key=lambda x: (x[2]["pctWithin200"], -x[2]["pctAnalysed"]))
        chosen[mode] = best
        raw = _params_with(raw, mode, best[0], best[1])
    keys = ("looksPerMin", "pctAnalysed", "pctWithin200", "p95Ms", "cutRecall", "falseCutsPerMin")
    raw["tuned"] = {
        "by": "2.2.3",
        "on": [json.loads(sj.read_text(encoding="utf-8"))["sessionId"] for sj, _, _ in items],
        "metrics": {
            m: {"tile_level": c[0], "min_immediate_gap_ms": c[1], **{k: c[2][k] for k in keys}}
            for m, c in chosen.items()
        },
    }
    gk.PARAMS.write_text(json.dumps(raw, indent=1) + "\n", encoding="utf-8")
    CHART.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 4.5), dpi=110)
    col = {"light": "#2a9d8f", "balanced": "#264653", "strict": "#e76f51"}
    for mode in MODES:
        xs = [x[2]["looksPerMin"] for x in pts[mode]]
        ys = [min(x[2]["p95Ms"] or 0, 2000) for x in pts[mode]]
        ax.scatter(xs, ys, c=col[mode], label=mode, s=28, alpha=0.8)
        c = chosen[mode][2]
        ax.scatter(
            [c["looksPerMin"]], [min(c["p95Ms"] or 0, 2000)], s=170, facecolors="none",
            edgecolors="black", linewidths=1.8,
        )  # fmt: skip
    ax.axhline(200, ls="--", c="gray", lw=1)
    ax.set_xlabel("looks per minute")
    ax.set_ylabel("p95 time to first look (ms, capped 2000)")
    ax.set_title("Look budget vs latency (ringed = chosen default)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(CHART)
    plt.close(fig)
    write_report(raw, chosen)
    for m, c in chosen.items():
        print(
            f"{m}: tile_level={c[0]} gap={c[1]} analysed={c[2]['pctAnalysed']:.1f}% "
            f"within200={c[2]['pctWithin200']:.1f}%"
        )
    return 0


def write_report(raw, chosen) -> None:
    ids = ", ".join(raw["tuned"]["on"])
    lines = [
        SECTION,
        "",
        f"Tuned on synthetic dev sessions: {ids}. Real dev recordings: PENDING-HUMAN (HC-2.2).",
        "",
        "| mode | tile_level | min gap ms | looks/min | % frames analysed | % within 200 ms | "
        "p95 ms | cut recall % | false cuts/min |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for m, c in chosen.items():
        r = c[2]
        lines.append(
            f"| {m} | {c[0]} | {c[1]} | {r['looksPerMin']:.1f} | {r['pctAnalysed']:.1f} | "
            f"{r['pctWithin200']:.1f} | {r['p95Ms']} | {r['cutRecall']:.0f} | "
            f"{r['falseCutsPerMin']:.2f} |"
        )
    lines += ["", "Per situation (% frames analysed, chosen params):", ""]
    lines += ["| mode | " + " | ".join(SITS) + " |", "|---|---|---|---|---|---|"]
    for m, c in chosen.items():
        s = c[2]["situations"]
        cells = [f"{s[k]['pct']:.1f}" if k in s else "-" for k in SITS]
        lines.append(f"| {m} | " + " | ".join(cells) + " |")
    b = chosen["balanced"][2]
    lines += [
        "",
        f"Scene cuts (Balanced): recall {b['cutRecall']:.0f}%, false cuts "
        f"{b['falseCutsPerMin']:.2f}/min (AC-2.2-02).",
        "",
    ]
    if b["pctAnalysed"] >= 15:
        lines += [
            "**Waiver proposed for AC-2.2-05 (DV-6):** Balanced analyses "
            f"{b['pctAnalysed']:.1f}% of frames (>= 15%) while AC-2.2-06 passes.",
            "",
        ]
    lines += ["![look budget](img/ch2-look-budget.png)", ""]
    text = "\n".join(lines)
    old = REPORT.read_text(encoding="utf-8") if REPORT.exists() else "# Chapter 2: Motion\n\n"
    if SECTION in old:
        head, _, rest = old.partition(SECTION)
        nxt = rest.find("\n## ")
        tail = rest[nxt + 1 :] if nxt >= 0 else ""
        old = head + text + ("\n" + tail if tail else "")
    else:
        old = old.rstrip() + "\n\n" + text
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(old, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m workshop.twin.budget")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("eval", "tune"):
        s = sub.add_parser(name)
        s.add_argument("--sessions", type=Path, default=Path("data/ch2/synth-dev"))
        s.add_argument("--labels", type=Path, default=Path("data/ch2/synth-dev/labels"))
        s.add_argument("--split", default=None)
        s.add_argument("--cut-tile-level", type=int, default=24)
        s.add_argument("--out", type=Path, default=Path("data/ch2/look-budget"))
    a = p.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    if a.sessions == Path("data/ch2/synth-dev"):
        ensure_dev_set(a.sessions)
    return cmd_eval(a) if a.cmd == "eval" else cmd_tune(a)


if __name__ == "__main__":
    raise SystemExit(main())
