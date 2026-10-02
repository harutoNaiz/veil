"""Motion scorer (2.3.3): time to cover, flicker, wrong covers, coverage, glue, frames analysed.

CLI: python -m workshop.eval.score_motion SESSION TAPE_OUT LABEL
     python -m workshop.eval.score_motion agree machine.csv human.csv
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from workshop.labels.recordings import boxes_at
from workshop.twin.oracle import DEFAULT_CONCEPTS, full_sizes, load_truth
from workshop.twin.tracker import covered_pct

INF = 10**9
ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "docs" / "reports" / "ch2-motion.md"
SECTION = "## Steady covers (Phase 2.3)"


def percentile(vals: list[int], pct: int) -> int:
    """Nearest rank: sorted[ceil(pct * n / 100) - 1]."""
    v = sorted(vals)
    return v[max(0, -(-pct * len(v) // 100) - 1)]


def _clip(r: dict, sw: int, sh: int) -> dict | None:
    x0, y0 = max(0, r["x"]), max(0, r["y"])
    x1, y1 = min(sw, r["x"] + r["w"]), min(sh, r["y"] + r["h"])
    if x1 <= x0 or y1 <= y0:
        return None
    return {"x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0}


def _inter(a: dict, b: dict) -> int:
    w = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])
    h = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"])
    return max(0, w) * max(0, h)


def _situation(scene: str, t: int, scroll_ts: list[int]) -> str:
    if scene in ("feed", "grid") and any(abs(t - s) <= 300 for s in scroll_ts):
        return "feedScroll"
    return scene if scene in ("reels", "video") else "static"


def analyse(session_json: Path, tape_out: Path, label: dict | None) -> dict:
    session_json = Path(session_json)
    s = json.loads(session_json.read_text(encoding="utf-8"))
    sid, fps = s["sessionId"], s["fps"]
    sw, sh = s["screenWidth"], s["screenHeight"]
    truth_p = session_json.parent / f"{sid}.truth.jsonl"
    truth = load_truth(truth_p) if truth_p.exists() else None
    sizes = full_sizes(truth) if truth else {}
    events_p = session_json.parent / f"{sid}.events.jsonl"
    scroll_ts = []
    if events_p.exists():
        for ln in events_p.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                e = json.loads(ln)
                if e.get("type") == "scrolled":
                    scroll_ts.append(e["tMs"])
    plans, looks, cache = {}, 0, []
    for ln in Path(tape_out).read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        r = json.loads(ln)
        if r["kind"] == "maskPlan":
            plans[r["frameId"]] = (r["tMs"], r["plan"]["masks"])
        elif r["kind"] == "look" and r["look"]:
            looks += 1
        elif r["kind"] == "cache":
            cache.append(r)
    fids = sorted(plans)
    times = [plans[f][0] for f in fids]
    # per frame visible boxes: key -> (clipped rect, covered, full)
    vis_rows: list[dict[str, tuple]] = []
    for f in fids:
        t, masks = plans[f]
        if truth is not None:
            raw = [
                (b["key"], b["rect"])
                for b in truth.get(f, {"boxes": []})["boxes"]
                if b["conceptId"] in DEFAULT_CONCEPTS
            ]
        elif label is not None:
            raw = [
                (b.get("key", str(i)), b["rect"])
                for i, b in enumerate(boxes_at(label, t))
                if b.get("conceptId", "cats") in DEFAULT_CONCEPTS
            ]
        else:
            raw = []
        row = {}
        for key, rect in raw:
            c = _clip(rect, sw, sh)
            if c is None:
                continue
            full = sizes[key][0] * sizes[key][1] if key in sizes else rect["w"] * rect["h"]
            if c["w"] * c["h"] * 2 < full:
                continue
            cov = covered_pct(c, [m["rect"] for m in masks]) >= 80
            whole = c == rect and (key not in sizes or (rect["w"], rect["h"]) == sizes[key])
            row[key] = (c, cov, whole)
        vis_rows.append(row)
    keys = sorted({k for row in vis_rows for k in row})
    n = len(fids)
    out: dict = {"ttc": [], "recover": [], "flicker": [], "wrong": [], "glue": []}
    vis_frames = cov_frames = 0
    for k in keys:
        prev_vis = False
        for i in range(n):
            v = k in vis_rows[i]
            if v:
                vis_frames += 1
                cov_frames += vis_rows[i][k][1]
            if v and not prev_vis:
                j = i
                while j < n and k in vis_rows[j] and not vis_rows[j][k][1]:
                    j += 1
                ttc = times[j] - times[i] if j < n and k in vis_rows[j] else INF
                out["ttc"].append((times[i], ttc, k))
                if any(
                    k in vis_rows[q] and vis_rows[q][k][1] and times[i] - times[q] <= 3000
                    for q in range(i - 1, -1, -1)
                    if times[i] - times[q] <= 3000
                ):
                    out["recover"].append(ttc)
            prev_vis = v
        for a in range(n - 1):
            if not (k in vis_rows[a] and vis_rows[a][k][1]):
                continue
            b = a + 1
            while b < n and k in vis_rows[b] and not vis_rows[b][k][1]:
                b += 1
            if b > a + 1 and b < n and k in vis_rows[b] and times[b] - times[a + 1] <= 1000:
                out["flicker"].append(times[a + 1])
    # clean stretches and wrong covers
    spans = [(c["startMs"], c["endMs"]) for c in label["clean"]] if label else None
    clean_idx, wrong_frames = [], []
    for i in range(n):
        t = times[i]
        clean = (
            any(a <= t <= b for a, b in spans) if spans is not None else not vis_rows[i]
        ) and not vis_rows[i]
        if not clean:
            continue
        clean_idx.append(i)
        for m in plans[fids[i]][1]:
            area = m["rect"]["w"] * m["rect"]["h"]
            if not any(_inter(m["rect"], c) * 10 >= area for c, _, _ in vis_rows[i].values()):
                wrong_frames.append(i)
                break
    prev = -2
    for i in wrong_frames:
        if i != prev + 1:
            out["wrong"].append(times[i])
        prev = i
    # glue
    for i in range(n):
        lo = times[i - 1] if i else times[i] - 1
        if not any(lo < t <= times[i] for t in scroll_ts):
            continue
        for c, cov, whole in vis_rows[i].values():
            if not (cov and whole):
                continue
            best = None
            for m in plans[fids[i]][1]:
                if len(m["trackIds"]) != 1:
                    continue
                inter = _inter(m["rect"], c)
                if inter * 100 >= 80 * c["w"] * c["h"] and (best is None or inter > best[0]):
                    best = (inter, m["rect"])
            if best:
                mr = best[1]
                dx = abs(mr["x"] + mr["w"] // 2 - (c["x"] + c["w"] // 2))
                dy = abs(mr["y"] + mr["h"] // 2 - (c["y"] + c["h"] // 2))
                out["glue"].append((times[i], max(dx, dy)))
    out.update(
        n=n, fps=fps, sid=sid, looks=looks, vis_frames=vis_frames, cov_frames=cov_frames,
        clean_frames=len(clean_idx), wrong_frames=len(wrong_frames), cache=cache,
        scenes=(
            [truth.get(f, {}).get("scene", "") for f in fids] if truth else [""] * n
        ),
        times=times,
        scroll_ts=scroll_ts,
    )  # fmt: skip
    return out


def score(session_json: Path, tape_out: Path, label: dict | None = None) -> dict:
    a = analyse(session_json, tape_out, label)
    ttc = sorted(x[1] for x in a["ttc"])
    glue = sorted(g for _, g in a["glue"])
    clean_min = a["clean_frames"] / a["fps"] / 60
    n = a["n"]
    dur_min = n / a["fps"] / 60 if n else 0
    sit: dict[str, dict] = {}
    for r in a["cache"]:
        sc = r.get("x", {}).get("situation", "static")
        d = sit.setdefault(sc, {"hits": 0, "misses": 0})
        d["hits"] += r["hits"]
        d["misses"] += r["misses"]
    for d in sit.values():
        tot = d["hits"] + d["misses"]
        d["hit_pct"] = round(100 * d["hits"] / tot, 1) if tot else 0.0
    cov = round(100 * a["cov_frames"] / a["vis_frames"], 2) if a["vis_frames"] else 100.0
    return {
        "sessionId": a["sid"],
        "appearances": len(ttc),
        "ttc_median_ms": ttc[(len(ttc) - 1) // 2] if ttc else 0,
        "ttc_p95_ms": percentile(ttc, 95) if ttc else 0,
        "coverage_pct": cov,
        "flicker": len(a["flicker"]),
        "flicker_per_min": round(len(a["flicker"]) / dur_min, 3) if dur_min else 0,
        "wrong_covers": len(a["wrong"]),
        "wrong_per_min": round(len(a["wrong"]) / clean_min, 3) if clean_min else 0.0,
        "wrong_sec_per_min": round(a["wrong_frames"] / a["fps"] / clean_min, 3) if clean_min else 0,
        "clean_min": round(clean_min, 4),
        "glue_median_px": glue[len(glue) // 2] if glue else 0,
        "analysed_pct": round(100 * a["looks"] / n, 2) if n else 0.0,
        "recover_max_ms": max(a["recover"]) if a["recover"] else None,
        "cache": {"situation": sit},
        "ttc_list": ttc,
        "glue_list": glue,
        "vis_frames": a["vis_frames"],
        "cov_frames": a["cov_frames"],
        "frames": n,
        "looks": a["looks"],
    }


def marks(session_json: Path, tape_out: Path, label: dict | None = None) -> list[dict]:
    a = analyse(session_json, tape_out, label)
    sid = a["sid"]
    out = [{"tMs": t, "session": sid, "type": "late"} for t, ttc, _ in a["ttc"] if ttc > 300]
    out += [{"tMs": t, "session": sid, "type": "flicker"} for t in a["flicker"]]
    out += [{"tMs": t, "session": sid, "type": "slide"} for t, g in a["glue"] if g > 16]
    out += [{"tMs": t, "session": sid, "type": "wrong"} for t in a["wrong"]]
    return sorted(out, key=lambda m: (m["tMs"], m["type"]))


# ---------------------------------------------------------------- agree
def _read_marks(p: Path) -> list[dict]:
    with open(p, newline="", encoding="utf-8") as f:
        return [
            {"tMs": int(r["tMs"]), "session": r["session"], "type": r["type"]}
            for r in csv.DictReader(f)
        ]


def agree(machine: list[dict], human: list[dict]) -> tuple[bool, list[str]]:
    def near(m, pool):
        return any(
            p["type"] == m["type"]
            and p["session"] == m["session"]
            and abs(p["tMs"] - m["tMs"]) <= 500
            for p in pool
        )

    issues = [f"human mark unmatched: {h}" for h in human if not near(h, machine)]
    issues += [
        f"machine {m['type']} not marked by human: {m}"
        for m in machine
        if m["type"] in ("flicker", "wrong") and not near(m, human)
    ]
    return not issues, issues


def write_marks_csv(path: Path, rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["tMs", "session", "type"])
        w.writeheader()
        w.writerows(rows)


# ---------------------------------------------------------------- report
def _row(mode: str, a: dict) -> str:
    return (
        f"| {mode} | {a['ttc_median_ms']} | {a['ttc_p95_ms']} | {a['flicker']} | "
        f"{a['wrong_per_min']} | {a['coverage_pct']} | {a['glue_median_px']} | "
        f"{a['analysed_pct']} | {a['appearances']} | {a['frames']} |"
    )


def write_report(scores_path: str, torture_path: str | None, fallback_path: str | None) -> None:
    sc = json.loads(Path(scores_path).read_text(encoding="utf-8"))
    head = "| mode | ttc median ms | ttc p95 ms | flicker | wrong/min | coverage % | glue px "
    head += (
        "| frames analysed % | appearances | frames |\n|---|---|---|---|---|---|---|---|---|---|"
    )
    lines = [
        SECTION,
        "",
        "Synthetic test sessions (oracle detector, 100 ms latency, self-capture on).",
    ]
    lines += ["Real recordings: PENDING-HUMAN (HC-2.3).", "", head]
    for m, v in sc["modes"].items():
        lines.append(_row(m, v["aggregate"]))
    g = sc.get("gate")
    if g:
        lines += ["", "Acceptance (Balanced):", ""]
        for k, (ok, val) in g["ac"].items():
            lines.append(f"- {k}: {'PASS' if ok else 'FAIL'} ({val})")
    lines += [
        "",
        "Cache hit rate per situation (Balanced, near-duplicate crops from the truth):",
        "",
    ]
    lines += ["| situation | hits | misses | hit % |", "|---|---|---|---|"]
    bal = sc["modes"].get("balanced", {}).get("aggregate", {}).get("cache", {})
    for k, v in sorted(bal.items()):
        lines.append(f"| {k} | {v['hits']} | {v['misses']} | {v['hit_pct']} |")
    if torture_path and Path(torture_path).exists():
        tt = json.loads(Path(torture_path).read_text(encoding="utf-8"))
        lines += ["", "PT-2.3 torture (torture-22, Balanced):", "", head]
        for m, v in tt["modes"].items():
            lines.append(_row(m, v["aggregate"]))
        b = tt["modes"].get("balanced", {}).get("aggregate", {})
        lines.append(f"\nre-cover max {b.get('recover_max_ms')} ms.")
    lines += ["", "### Chapter 2 gate decision", ""]
    if g:
        lines.append(
            f"GATE {g['name']}: **{'PASS' if g['pass'] else 'FAIL'}** (real gate: PENDING-HUMAN)."
        )
    if fallback_path and Path(fallback_path).exists():
        fb = json.loads(Path(fallback_path).read_text(encoding="utf-8"))
        lines += [
            "",
            "PLAN fallback run (`--fallback`: solid only, holds x2, rates x2; report-only):",
            "",
            head,
        ]
        for m, v in fb["modes"].items():
            lines.append(_row(m, v["aggregate"]))
        if fb.get("gate"):
            lines.append(f"\nfallback GATE: {'PASS' if fb['gate']['pass'] else 'FAIL'}")
    lines += [
        "",
        "Deviations: DV-1 oracle detector (real detector DEFERRED); DV-2 synthetic gate; DV-3 cats "
        "(L2) + spiders (L1 stand-in); DV-4 confirm looks; DV-5 scene cut ends self-capture hold; "
        "DV-6 whole-post covers deferred; DV-7 64-bit DCT cache hash.",
        "",
        "Videos: [feed](media/ch2-feed.mp4), [reels](media/ch2-reels.mp4), "
        "[video](media/ch2-video.mp4).",
        "",
    ]
    text = "\n".join(lines)
    cur = REPORT.read_text(encoding="utf-8") if REPORT.exists() else "# Chapter 2: Motion\n"
    if SECTION in cur:
        pre, rest = cur.split(SECTION, 1)
        nxt = rest.find("\n## ")
        post = rest[nxt + 1 :] if nxt >= 0 else ""
        cur = pre.rstrip() + "\n\n" + text + ("\n" + post if post else "")
    else:
        cur = cur.rstrip() + "\n\n" + text
    REPORT.write_text(cur, encoding="utf-8")


def main(argv: list[str]) -> int:
    if argv and argv[0] == "agree":
        ok, issues = agree(_read_marks(Path(argv[1])), _read_marks(Path(argv[2])))
        for i in issues:
            print(i)
        print("AGREE: PASS" if ok else "AGREE: FAIL")
        return 0 if ok else 1
    if argv and argv[0] == "marks-csv":  # marks-csv OUT.csv EVAL_DIR SESSION_JSON...
        rows = []
        for sj in argv[3:]:
            sp = Path(sj)
            sid = json.loads(sp.read_text(encoding="utf-8"))["sessionId"]
            lp = sp.parent / "labels" / f"{sid}.json"
            label = json.loads(lp.read_text(encoding="utf-8")) if lp.exists() else None
            rows += marks(sp, Path(argv[2]) / "balanced" / f"{sid}.tape-out.jsonl", label)
        write_marks_csv(Path(argv[1]), rows)
        print(f"MARKS {len(rows)} -> {argv[1]}")
        return 0
    if argv and argv[0] == "check-pt":  # check-pt SCORES_JSON SESSION_ID
        b = json.loads(Path(argv[1]).read_text(encoding="utf-8"))["modes"]["balanced"]
        r = b["sessions"][argv[2]]
        rec = r["recover_max_ms"]
        checks = {
            "No flicker anywhere": r["flicker"] == 0,
            "Covers stay glued during fast flings": r["glue_median_px"] <= 8,
            "A cat scrolled away and back is covered again immediately": rec is None or rec <= 34,
            "Covers usually appear before the reviewer can make out the cat": r["ttc_median_ms"]
            <= 300,
        }
        for k, ok in checks.items():
            print(f"{'PASS' if ok else 'FAIL'} {k}")
        print(f"VALUES flicker={r['flicker']} glue={r['glue_median_px']} recover={rec}")
        return 0 if all(checks.values()) else 1
    if argv and argv[0] == "print-flicker":
        r = json.loads(Path(argv[1]).read_text(encoding="utf-8"))["modes"]["balanced"]["sessions"]
        print(f"INFO rule-off flicker={r[argv[2]]['flicker']}")
        return 0
    if len(argv) != 3:
        print("usage: score_motion SESSION TAPE_OUT LABEL | agree MACHINE HUMAN")
        return 2
    lp = Path(argv[2])
    label = json.loads(lp.read_text(encoding="utf-8")) if lp.exists() else None
    r = score(Path(argv[0]), Path(argv[1]), label)
    r.pop("ttc_list"), r.pop("glue_list")
    print(json.dumps(r, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
