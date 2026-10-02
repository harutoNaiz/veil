"""2.2.3 Timeline: idle padding, look timeline chart and the PT-2.2 machine checks."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
from pathlib import Path

IDLE_FRAMES_PER_S = 30
COLORS = {
    "sceneCut": "#d62828", "appChange": "#6a4c93", "swipe": "#f77f00", "revealedStrip": "#fcbf49",
    "periodic": "#2a9d8f", "checkup": "#1d3557",
}  # fmt: skip


def _jl(path: Path) -> list[dict]:
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]


def pad_idle(session_json: Path, out_dir: Path, idle_ms: int = 30000) -> Path:
    sj = Path(session_json)
    out = Path(out_dir)
    (out / "labels").mkdir(parents=True, exist_ok=True)
    s = json.loads(sj.read_text(encoding="utf-8"))
    sid, nid, t0, fps = s["sessionId"], s["sessionId"] + "-idle", s["t0Ms"], s["fps"]
    extra = idle_ms * fps // 1000
    src = sj.parent
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src / s["video"]), "-vf",
         f"tpad=start_duration={idle_ms // 1000}:start_mode=clone", "-r", str(fps),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(out / f"{nid}.mp4")],
        check=True,
    )  # fmt: skip
    ev = _jl(src / f"{sid}.events.jsonl")
    for e in ev:
        e["tMs"] += idle_ms
    (out / f"{nid}.events.jsonl").write_text(
        "".join(json.dumps(e, sort_keys=True) + "\n" for e in ev), encoding="utf-8"
    )
    tp = src / f"{sid}.truth.jsonl"
    if tp.exists():
        tr = _jl(tp)
        pre = []
        for i in range(extra):
            pre.append({**tr[0], "i": i, "tMs": t0 + (i * 1000) // fps})
        for r in tr:
            r["i"] += extra
            r["tMs"] += idle_ms
        (out / f"{nid}.truth.jsonl").write_text(
            "".join(json.dumps(r) + "\n" for r in pre + tr), encoding="utf-8"
        )
    dp = src / f"{sid}.driver.json"
    if dp.exists():
        d = json.loads(dp.read_text(encoding="utf-8"))
        for r in d:
            r["tMs"] += idle_ms
        (out / f"{nid}.driver.json").write_text(json.dumps(d), encoding="utf-8")
    lp = src / "labels" / f"{sid}.json"
    if lp.exists():
        lab = json.loads(lp.read_text(encoding="utf-8"))
        lab["sessionId"] = nid
        lab["durationMs"] += idle_ms
        for tr_ in lab["tracks"]:
            for sp in tr_["spans"]:
                first = sp["startMs"] == t0
                sp["startMs"] = t0 if first else sp["startMs"] + idle_ms
                sp["endMs"] += idle_ms
            kf = [{"tMs": k["tMs"] + idle_ms, "rect": k["rect"]} for k in tr_["keyframes"]]
            if any(sp["startMs"] == t0 for sp in tr_["spans"]):
                kf.insert(0, {"tMs": t0, "rect": kf[0]["rect"]})
            tr_["keyframes"] = kf
        for m in lab["marks"]:
            m["tMs"] += idle_ms
        for c in lab["clean"]:
            c["startMs"] = t0 if c["startMs"] == t0 else c["startMs"] + idle_ms
            c["endMs"] += idle_ms
        (out / "labels" / f"{nid}.json").write_text(json.dumps(lab), encoding="utf-8")
    s["sessionId"], s["video"] = nid, f"{nid}.mp4"
    s["frameCount"] += extra
    path = out / f"{nid}.session.json"
    path.write_text(json.dumps(s, indent=1), encoding="utf-8")
    return path


def _looks(tape_out: Path) -> list[dict]:
    return [r for r in _jl(tape_out) if r["kind"] == "look"]


def chart(tape_in: Path, tape_out: Path, session_json: Path, png: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    recs = _jl(tape_out)
    ev = [r["event"] for r in _jl(tape_in) if r["kind"] == "event"]
    sj = Path(session_json)
    s = json.loads(sj.read_text(encoding="utf-8"))
    t0 = s["t0Ms"]
    fig, ax = plt.subplots(4, 1, figsize=(14, 7), sharex=True, dpi=100)
    ch = [r for r in recs if r["kind"] == "change"]
    ax[0].plot([(r["tMs"] - t0) / 1000 for r in ch], [r["changedTiles"] for r in ch], lw=0.8)
    ax[0].set_ylabel("changed tiles")
    sc = [e for e in ev if e.get("type") == "scrolled"]
    ax[1].vlines([(e["tMs"] - t0) / 1000 for e in sc], 0, [e["dy"] for e in sc], lw=0.8)
    ax[1].set_ylabel("scroll dy")
    lk = [r for r in _looks(tape_out) if r["look"]]
    for why, c in COLORS.items():
        xs = [(r["tMs"] - t0) / 1000 for r in lk if r["reason"] == why]
        ax[2].scatter(xs, [0] * len(xs), c=c, s=22, label=why, marker="|")
    busy = [(r["tMs"] - t0) / 1000 for r in _looks(tape_out) if r["reason"] == "busy"]
    ax[2].scatter(busy, [0.4] * len(busy), c="gray", s=6, label="busy")
    ax[2].set_ylabel("looks")
    ax[2].legend(ncol=7, fontsize=7, loc="upper right")
    tp = sj.parent / f"{s['sessionId']}.truth.jsonl"
    if tp.exists():
        names = sorted({r["scene"] for r in _jl(tp)})
        for r in _jl(tp)[::3]:
            ax[3].plot((r["tMs"] - t0) / 1000, names.index(r["scene"]), "s", ms=3, c="#555")
        ax[3].set_yticks(range(len(names)), names, fontsize=7)
    lp = sj.parent / "labels" / f"{s['sessionId']}.json"
    if lp.exists():
        for m in json.loads(lp.read_text(encoding="utf-8"))["marks"]:
            for a in ax:
                a.axvline((m["tMs"] - t0) / 1000, c="#d62828", lw=0.5, alpha=0.5)
            ax[3].text((m["tMs"] - t0) / 1000, 0, m["type"], rotation=90, fontsize=6)
    ax[3].set_xlabel("session time (s)")
    fig.tight_layout()
    Path(png).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(png)
    plt.close(fig)


def _line(name: str, ok: bool, info: str = "") -> dict:
    print(f"{'PASS' if ok else 'FAIL'}  {name} {info}".rstrip())
    return {"name": name, "ok": ok, "info": info}


def pt_checks(session_json, tape_in, out_normal, out_slow, idle=None, label=None) -> dict:
    """The PT-2.2 machine checks. `idle` = (startMs, endMs) or None."""
    from workshop.twin import budget

    sj = Path(session_json)
    s = json.loads(sj.read_text(encoding="utf-8"))
    ev = [r["event"] for r in _jl(tape_in) if r["kind"] == "event"]
    res: list[dict] = []
    nl, sl = _looks(out_normal), _looks(out_slow)
    if idle:
        a, b = idle
        il = [r for r in nl if a <= r["tMs"] < b and r["look"]]
        ok = bool(il) and all(r["reason"] == "checkup" for r in il) and len(il) in (6, 7)
        res.append(_line("idle only check-ups", ok, f"{len(il)} looks"))
    # triggers
    trig: list[tuple[int, str]] = []
    prev = None
    for e in ev:
        if e.get("type") == "scrolled":
            if prev is None or e["tMs"] - prev > 150:
                trig.append((e["tMs"], "scrollStart"))
            prev = e["tMs"]
    if label:
        trig += [(m["tMs"], m["type"]) for m in label["marks"] if m["type"] != "lock"]
    for name, looks, lim in (("normal", nl, 200), ("slow", sl, 700)):
        yes = [r["tMs"] for r in looks if r["look"]]
        miss = [t for t in trig if not any(t[0] <= y <= t[0] + lim for y in yes)]
        res.append(_line(f"trigger looks within {lim} ms ({name})", not miss,
                         f"{len(trig) - len(miss)}/{len(trig)} {miss[:3]}"))  # fmt: skip
    tp = sj.parent / f"{s['sessionId']}.truth.jsonl"
    if tp.exists():
        vid = {r["i"] for r in _jl(tp) if r["scene"] == "video"}
        vl = [r["tMs"] for r in nl if r["look"] and r["frameId"] in vid
              and r["reason"] in ("periodic", "revealedStrip")]  # fmt: skip
        worst = max((sum(1 for y in vl if t <= y < t + 1000) for t in vl), default=0)
        res.append(_line("video <= 3 periodic/strip looks per second", worst <= 3, f"max {worst}"))
    sy = [r["tMs"] for r in sl if r["look"]]
    gaps_ok = all(b - a >= 500 for a, b in zip(sy, sy[1:], strict=False))
    nb = sum(1 for r in sl if r["reason"] == "busy")
    final = sl[-1]["x"]["skipped"] if sl else 0
    res.append(_line("slow: looks >= 500 ms apart", gaps_ok))
    res.append(_line("slow: queue always 0", all(r["x"]["queue"] == 0 for r in sl)))
    res.append(_line("slow: busy records == skipped > 0", nb == final and nb > 0, f"{nb}/{final}"))
    ac5 = ac6 = None
    if label:
        m = budget.derive(budget.merge([budget.evaluate(sj, label, tape_in, "balanced")]))
        ac5, ac6 = m["pctAnalysed"], m["pctWithin200"]
        print(f"INFO  AC-2.2-05 {ac5:.1f}% analysed ({'PASS' if ac5 < 15 else 'above 15%'})")
        res.append(_line("AC-2.2-06 >= 95% within 200 ms", ac6 >= 95, f"{ac6:.1f}%"))
    return {"checks": res, "ok": all(c["ok"] for c in res), "ac05": ac5, "ac06": ac6}


def cmd_pt(a) -> int:
    from workshop.recordings.synth_session import generate
    from workshop.replay.player import replay
    from workshop.replay.tape import validate_file
    from workshop.twin.gatekeeper import GatekeeperPipeline

    out = a.out
    if a.session:
        sj, label = Path(a.session), None
        lp = sj.parent / "labels" / f"{sj.name.split('.')[0]}.json"
        if lp.exists():
            label = json.loads(lp.read_text(encoding="utf-8"))
        idle = (a.idle_start_ms, a.idle_end_ms) if a.idle_start_ms is not None else None
        if out.exists():
            shutil.rmtree(out)
    else:
        if out.exists():
            shutil.rmtree(out)
        work = out / "work"
        base = generate(work, "pt22", seconds=150, seed=22)
        sj = pad_idle(base, work)
        label = json.loads((work / "labels" / "pt22-idle.json").read_text(encoding="utf-8"))
        t0 = json.loads(sj.read_text(encoding="utf-8"))["t0Ms"]
        idle = (t0, t0 + 30000)
    out.mkdir(parents=True, exist_ok=True)
    tapes = {}
    for name, ms in (("normal", 0), ("slow", 500)):
        r = replay(sj, GatekeeperPipeline("balanced", None, ms), out / name, video=False)
        tapes[name] = (r.tape_in, r.tape_out)
    bad = 0
    for t in tapes.values():
        for p in t:
            bad += len(validate_file(p))
    print(f"{'PASS' if not bad else 'FAIL'}  tape validate ({bad} errors)")
    res = pt_checks(sj, tapes["normal"][0], tapes["normal"][1], tapes["slow"][1], idle, label)
    chart(tapes["normal"][0], tapes["normal"][1], sj, out / "timeline.png")
    chart(tapes["slow"][0], tapes["slow"][1], sj, out / "timeline-slow.png")
    with open(out / "looks.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["run", "tMs", "frameId", "reason", "state"])
        for name, t in tapes.items():
            for r in _looks(t[1]):
                if r["look"]:
                    w.writerow([name, r["tMs"], r["frameId"], r["reason"], r["state"]])
    res["tapeErrors"] = bad
    (out / "pt.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    ok = res["ok"] and not bad
    print("PT 2.2: PASS (machine)" if ok else "PT 2.2: FAIL")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m workshop.twin.timeline")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("pt")
    s.add_argument("--out", type=Path, default=Path("data/evidence/pt-2.2"))
    s.add_argument("--session")
    s.add_argument("--idle-start-ms", type=int)
    s.add_argument("--idle-end-ms", type=int)
    a = p.parse_args(argv)
    return cmd_pt(a)


if __name__ == "__main__":
    raise SystemExit(main())
