"""Golden tapes (2.3.3): freeze and check. CLI: python -m workshop.twin.goldens freeze|check"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import shutil
import sys
from pathlib import Path

from workshop.replay.player import replay
from workshop.replay.tape import dumps, validate_file
from workshop.twin.motion import MotionPipeline, run_tape
from workshop.twin.motion_synth import generate
from workshop.twin.oracle import OracleParams

GOLDENS = (("feed-scroll", "feed", 31), ("reels", "reels", 32), ("video", "video", 33))
KINDS = ("change", "look", "tracks", "maskPlan")
SESSIONS = Path("data/ch2/golden")


def _records(path: Path) -> list[dict]:
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]


def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def merge_tape_in(tape_in: Path, findings: list[dict]) -> list[dict]:
    """Insert each finding record right before its delivery frame; renumber seq."""
    by_frame: dict[int, list[dict]] = {}
    for f in findings:
        by_frame.setdefault(f["x"]["deliverFrameId"], []).append(f)
    out: list[dict] = []
    for r in _records(tape_in):
        if r["kind"] == "frame":
            out.extend(dict(f) for f in by_frame.get(r["frameId"], []))
        out.append(r)
    for i, r in enumerate(out):
        r["seq"] = i
    return out


def _write(path: Path, recs: list[dict]) -> None:
    Path(path).write_bytes(b"".join(dumps(r) for r in recs))


def _replay(sj: Path, out: Path, video: bool, **kw):
    pipe = MotionPipeline(sj, "balanced", use_cache=False, oracle=OracleParams(seed=0), **kw)
    res = replay(sj, pipe, out, self_capture=True, markers=False, video=video)
    return pipe, res


def freeze(out: str | Path = "contracts/tapes") -> list[dict]:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    SESSIONS.mkdir(parents=True, exist_ok=True)
    meta = []
    for name, script, seed in GOLDENS:
        sj = generate(SESSIONS, script, seed)
        work = SESSIONS / f"work-{name}"
        pipe, res = _replay(sj, work, video=False)
        recs = merge_tape_in(res.tape_in, pipe.findings_log)
        tin, tout = out / f"{name}.tape-in.jsonl", out / f"{name}.tape-out.jsonl"
        _write(tin, recs)
        _write(tout, _records(res.tape_out))
        meta.append(
            {
                "name": name, "sessionId": json.loads(sj.read_text())["sessionId"],
                "mode": "balanced", "oracle": dataclasses.asdict(OracleParams(seed=0)),
                "frames": res.frames, "tapeIn": tin.name, "tapeInSha256": _sha(tin),
                "tapeOut": tout.name, "tapeOutSha256": _sha(tout),
            }
        )  # fmt: skip
    (out / "tapes.json").write_text(json.dumps({"tapes": meta}, indent=1), encoding="utf-8")
    return meta


def _strip(recs: list[dict]) -> list[dict]:
    return [{k: v for k, v in r.items() if k != "seq"} for r in recs if r["kind"] in KINDS]


def check(out: str | Path = "contracts/tapes") -> bool:
    out = Path(out)
    meta = json.loads((out / "tapes.json").read_text(encoding="utf-8"))["tapes"]
    ok = len(meta) >= 3
    for m in meta:
        tin, tout = out / m["tapeIn"], out / m["tapeOut"]
        errs = validate_file(tin) + validate_file(tout)
        for e in errs:
            print(e)
        p = OracleParams(**m["oracle"])
        a = _strip(run_tape(tin, m["mode"], oracle=p))
        b = _strip(run_tape(tin, m["mode"], oracle=p))
        stored = _strip(_records(tout))
        good = not errs and a == b == stored
        print(f"{'OK' if good else 'FAIL'} {m['name']} frames={m['frames']} records={len(a)}")
        ok = ok and good
    return ok


def media(dest: str | Path = "docs/reports/media") -> None:
    from workshop.twin.motion import _sbs

    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    for name, script, seed in GOLDENS:
        sj = SESSIONS / f"{script}-{seed}.session.json"
        work = SESSIONS / f"vid-{name}"
        _, res = _replay(sj, work, video=True)
        sid = sj.name.removesuffix(".session.json")
        short = {"feed-scroll": "feed"}.get(name, name)
        tmp = work / f"{sid}.sbs.mp4"
        _sbs(sj.parent / f"{sid}.mp4", res.video, tmp)
        shutil.copyfile(tmp, dest / f"ch2-{short}.mp4")


def main(argv: list[str] | None = None) -> int:
    a = list(sys.argv[1:] if argv is None else argv)
    cmd = a[0] if a else ""
    path = a[1] if len(a) > 1 else "contracts/tapes"
    if cmd == "freeze":
        for m in freeze(path):
            print("FROZEN", m["name"], m["frames"])
        return 0
    if cmd == "check":
        good = check(path)
        print("GOLDENS: OK" if good else "GOLDENS: FAIL")
        return 0 if good else 1
    if cmd == "media":
        media()
        return 0
    print("usage: goldens freeze|check [DIR] | media")
    return 2


if __name__ == "__main__":
    sys.exit(main())
