"""Recording labels (Phase 2.1.2): schema, interpolation, LS video import, agree, freeze."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

SCHEMA_PATH = Path(__file__).with_name("recording-label.schema.json")
MAX_GAP_MS = 500


def validate(label: dict) -> list[str]:
    """Schema errors plus rule errors; empty list means valid."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8-sig"))
    errors = [
        f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}"
        for e in Draft202012Validator(schema).iter_errors(label)
    ]
    if errors:
        return errors
    all_spans = []
    for tr in label["tracks"]:
        k = tr["key"]
        kfs = tr["keyframes"]
        ts = [f["tMs"] for f in kfs]
        if ts != sorted(ts):
            errors.append(f"track {k}: keyframes not sorted")
        for sp in tr["spans"]:
            if sp["endMs"] < sp["startMs"]:
                errors.append(f"track {k}: span ends before it starts")
                continue
            all_spans.append((sp["startMs"], sp["endMs"], k))
            inside = sorted(t for t in ts if sp["startMs"] <= t <= sp["endMs"])
            if sp["startMs"] not in inside:
                errors.append(f"track {k}: span start {sp['startMs']} has no keyframe")
            if sp["endMs"] not in inside:
                errors.append(f"track {k}: span end {sp['endMs']} has no keyframe")
            for a, b in zip(inside, inside[1:], strict=False):
                if b - a > MAX_GAP_MS:
                    errors.append(f"track {k}: keyframe gap {b - a} ms > {MAX_GAP_MS} at {a}")
        for t in ts:
            if not any(s["startMs"] <= t <= s["endMs"] for s in tr["spans"]):
                errors.append(f"track {k}: keyframe at {t} outside spans")
    for c in label["clean"]:
        for s, e, k in all_spans:
            if c["startMs"] < e and s < c["endMs"]:
                errors.append(f"clean {c['startMs']}-{c['endMs']} overlaps track {k}")
    return errors


def _lerp(a: dict, b: dict, t: int) -> dict:
    t0, t1 = a["tMs"], b["tMs"]
    if t1 == t0:
        return dict(a["rect"])
    return {
        k: a["rect"][k] + ((b["rect"][k] - a["rect"][k]) * (t - t0)) // (t1 - t0)
        for k in ("x", "y", "w", "h")
    }


def boxes_at(label: dict, t_ms: int) -> list[dict]:
    out = []
    for tr in label["tracks"]:
        for sp in tr["spans"]:
            if not sp["startMs"] <= t_ms <= sp["endMs"]:
                continue
            kfs = [f for f in tr["keyframes"] if sp["startMs"] <= f["tMs"] <= sp["endMs"]]
            if not kfs:
                continue
            rect = None
            for a, b in zip(kfs, kfs[1:], strict=False):
                if a["tMs"] <= t_ms <= b["tMs"]:
                    rect = _lerp(a, b, t_ms)
                    break
            if rect is None:
                rect = dict(kfs[0]["rect"])
            out.append({"key": tr["key"], "conceptId": tr["conceptId"], "rect": rect})
            break
    return out


def _concept(label_value: str) -> str:
    for suffix in ("-emoji", "-text"):
        if label_value.endswith(suffix):
            return label_value[: -len(suffix)] + "s"
    return label_value


def from_ls(export: dict | list, session_json: Path) -> dict:
    """Convert one Label Studio video task export into a recording label."""
    sess = json.loads(Path(session_json).read_text(encoding="utf-8-sig"))
    task = export[0] if isinstance(export, list) else export
    anns = task.get("annotations") or []
    results = anns[0]["result"] if anns else []
    fps, t0 = sess["fps"], sess["t0Ms"]
    sw, sh = sess["screenWidth"], sess["screenHeight"]

    def t_of(frame: int) -> int:
        return t0 + ((frame - 1) * 1000) // fps

    tracks, marks, clean = [], [], []
    for n, r in enumerate(results):
        v = r.get("value", {})
        if r.get("type") == "videorectangle":
            lab = (v.get("labels") or ["unknown"])[0]
            seq = sorted(v.get("sequence", []), key=lambda s: s["frame"])
            kfs, spans, start = [], [], None
            for s in seq:
                t = t_of(s["frame"])
                rect = {
                    "x": round(s["x"] * sw / 100),
                    "y": round(s["y"] * sh / 100),
                    "w": round(s["width"] * sw / 100),
                    "h": round(s["height"] * sh / 100),
                }
                if s.get("enabled", True):
                    if start is None:
                        start = t
                    kfs.append({"tMs": t, "rect": rect})
                elif start is not None:
                    kfs.append({"tMs": t, "rect": rect})
                    spans.append({"startMs": start, "endMs": t})
                    start = None
            if start is not None:
                spans.append({"startMs": start, "endMs": kfs[-1]["tMs"]})
            spans = [s for s in spans if s["endMs"] >= s["startMs"]]
            tr = {
                "key": str(r.get("id", f"t{n}")),
                "conceptId": _concept(lab),
                "spans": spans,
                "keyframes": kfs,
            }
            _resample(tr)
            if tr["spans"]:
                tracks.append(tr)
        elif r.get("type") == "timelinelabels":
            for rg in v.get("ranges", []):
                for name in v.get("timelinelabels", []):
                    if name == "clean":
                        clean.append({"startMs": t_of(rg["start"]), "endMs": t_of(rg["end"])})
                    else:
                        marks.append({"tMs": t_of(rg["start"]), "type": name})
    marks.sort(key=lambda m: (m["tMs"], m["type"]))
    return {
        "labelVersion": "1",
        "sessionId": sess["sessionId"],
        "durationMs": (sess["frameCount"] * 1000) // fps,
        "screenWidth": sw,
        "screenHeight": sh,
        "labeller": "label-studio",
        "reviewedBy": None,
        "tracks": tracks,
        "marks": marks,
        "clean": clean,
    }


def _resample(tr: dict) -> None:
    """Insert interpolated keyframes so gaps inside spans are <= 500 ms."""
    base = list(tr["keyframes"])
    out = {f["tMs"]: f for f in base}
    for sp in tr["spans"]:
        kfs = [f for f in base if sp["startMs"] <= f["tMs"] <= sp["endMs"]]
        for a, b in zip(kfs, kfs[1:], strict=False):
            gap = b["tMs"] - a["tMs"]
            if gap > MAX_GAP_MS:
                parts = -(-gap // MAX_GAP_MS)
                for i in range(1, parts):
                    t = a["tMs"] + gap * i // parts
                    out[t] = {"tMs": t, "rect": _lerp(a, b, t)}
    tr["keyframes"] = [out[t] for t in sorted(out)]


def _iou(a: dict, b: dict) -> float:
    ix = max(0, min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"]))
    iy = max(0, min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"]))
    inter = ix * iy
    union = a["w"] * a["h"] + b["w"] * b["h"] - inter
    return inter / union if union else 0.0


def agree(a: dict, b: dict) -> float:
    """Disagreement in [0, 1]: unmatched boxes (both sides) plus unmatched marks over totals."""
    end = max(a["durationMs"], b["durationMs"])
    for lab in (a, b):
        for tr in lab["tracks"]:
            for sp in tr["spans"]:
                end = max(end, sp["endMs"])
    unmatched = total = 0
    for t in range(0, end + 1, MAX_GAP_MS):
        ba, bb = boxes_at(a, t), boxes_at(b, t)
        used: set[int] = set()
        matched = 0
        for x in ba:
            for j, y in enumerate(bb):
                if (
                    j not in used
                    and x["conceptId"] == y["conceptId"]
                    and _iou(x["rect"], y["rect"]) >= 0.5
                ):
                    used.add(j)
                    matched += 1
                    break
        total += len(ba) + len(bb)
        unmatched += len(ba) + len(bb) - 2 * matched
    for p, q in ((a["marks"], b["marks"]), (b["marks"], a["marks"])):
        unmatched += sum(
            1
            for m in p
            if not any(m["type"] == o["type"] and abs(m["tMs"] - o["tMs"]) <= MAX_GAP_MS for o in q)
        )
    return unmatched / total if total else 0.0


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _frozen_files(sid: str, labels_dir: Path, recordings_dir: Path) -> list[tuple[str, Path]]:
    return [
        (f"{sid}.mp4", Path(recordings_dir) / f"{sid}.mp4"),
        (f"{sid}.events.jsonl", Path(recordings_dir) / f"{sid}.events.jsonl"),
        (f"{sid}.label.json", Path(labels_dir) / f"{sid}.json"),
    ]


def split_freeze(labels_dir: Path, recordings_dir: Path) -> dict:
    labels_dir = Path(labels_dir)
    ids = sorted(p.stem for p in labels_dir.glob("*.json") if p.name != "split.json")
    ranked = sorted(ids, key=lambda s: hashlib.sha256(s.encode()).hexdigest())
    n_test = max(1, round(len(ids) / 3)) if ids else 0
    test = sorted(ranked[:n_test])
    dev = sorted(ranked[n_test:])
    split = {"dev": dev, "test": test}
    (labels_dir / "split.json").write_bytes(
        (json.dumps(split, sort_keys=True, indent=1) + "\n").encode("utf-8")
    )
    lines = []
    for sid in test:
        for name, p in _frozen_files(sid, labels_dir, recordings_dir):
            lines.append(f"{_sha(p)}  {name}\n")
    (labels_dir / "FROZEN.sha256").write_bytes("".join(lines).encode("utf-8"))
    return split


def check_frozen(labels_dir: Path, recordings_dir: Path) -> bool:
    labels_dir = Path(labels_dir)
    try:
        split = json.loads((labels_dir / "split.json").read_text(encoding="utf-8-sig"))
        want = (labels_dir / "FROZEN.sha256").read_text(encoding="utf-8").splitlines()
    except OSError:
        return False
    have = []
    for sid in split["test"]:
        for name, p in _frozen_files(sid, labels_dir, recordings_dir):
            if not p.exists():
                return False
            have.append(f"{_sha(p)}  {name}")
    return have == want


def _load(p: str) -> dict:
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m workshop.labels.recordings")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate").add_argument("files", nargs="+")
    p = sub.add_parser("agree")
    p.add_argument("a")
    p.add_argument("b")
    p = sub.add_parser("from-ls")
    p.add_argument("export")
    p.add_argument("session")
    p.add_argument("--out", required=True)
    for name in ("split-freeze", "check-frozen"):
        p = sub.add_parser(name)
        p.add_argument("labels_dir")
        p.add_argument("recordings_dir")
    a = ap.parse_args(argv)
    if a.cmd == "validate":
        bad = 0
        for f in a.files:
            errs = validate(_load(f))
            print(f"{'INVALID' if errs else 'OK'} {f}")
            for e in errs:
                print(f"  {e}")
            bad += bool(errs)
        return 1 if bad else 0
    if a.cmd == "agree":
        d = agree(_load(a.a), _load(a.b))
        print(f"DISAGREEMENT {d:.4f} {'PASS' if d <= 0.05 else 'FAIL'}")
        return 0 if d <= 0.05 else 1
    if a.cmd == "from-ls":
        label = from_ls(_load(a.export), Path(a.session))
        Path(a.out).write_text(json.dumps(label, indent=1) + "\n", encoding="utf-8")
        errs = validate(label)
        print("\n".join(errs) or f"OK {a.out}")
        return 1 if errs else 0
    if a.cmd == "split-freeze":
        s = split_freeze(Path(a.labels_dir), Path(a.recordings_dir))
        print(f"SPLIT dev={len(s['dev'])} test={len(s['test'])}")
        return 0
    ok = check_frozen(Path(a.labels_dir), Path(a.recordings_dir))
    print("FROZEN OK" if ok else "FROZEN FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
