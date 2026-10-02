"""2.2.3 Gatekeeper pipeline: change detector + burst scheduler on the 2.1 player."""

from __future__ import annotations

import argparse
import base64
import dataclasses
import json
from pathlib import Path

import numpy as np

from workshop.twin import change as ch
from workshop.twin import scheduler as sc

PARAMS = Path(__file__).with_name("params.json")


def _mk(cls, d: dict):
    names = {f.name for f in dataclasses.fields(cls)}
    kw = {k: v for k, v in d.items() if k in names}
    if "skip_packages" in kw:
        kw["skip_packages"] = tuple(kw["skip_packages"])
    return cls(**kw)


def default_raw() -> dict:
    modes = {}
    for name, mp in sc.MODES.items():
        modes[name] = {
            "change": dataclasses.asdict(ch.ChangeParams()),
            "sched": {**dataclasses.asdict(mp), "skip_packages": []},
        }
    return {"params_version": "1", "modes": modes, "tuned": {}}


def load_params(path: Path = PARAMS) -> dict[str, tuple[ch.ChangeParams, sc.ModeParams]]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return {
        m: (_mk(ch.ChangeParams, d["change"]), _mk(sc.ModeParams, d["sched"]))
        for m, d in raw["modes"].items()
    }


class GatekeeperPipeline:
    name = "gatekeeper-v1"

    def __init__(self, mode: str = "balanced", params: Path | dict | None = None, look_ms: int = 0):
        if params is None:
            params = PARAMS
        table = load_params(params) if isinstance(params, (str, Path)) else params
        if "modes" in table:  # raw params.json shape
            table = {
                m: (_mk(ch.ChangeParams, d["change"]), _mk(sc.ModeParams, d["sched"]))
                for m, d in table["modes"].items()
            }
        self.mode = mode
        self.cp, self.mp = table[mode]
        self.look_ms = look_ms
        self.state = sc.SchedState()
        self.ref: np.ndarray | None = None
        self.dy_since_ref = 0
        self.busy_until = -(10**9)
        self.queue: list = []  # never filled: a busy request is skipped, not queued
        self.package: str | None = None
        self._buf: list[dict] = []

    def on_event(self, event: dict) -> list[dict]:
        self._buf.append(event)
        return []

    def on_frame(self, frame_bgr: np.ndarray, frame: dict) -> list[dict]:
        return self.on_thumb(ch.thumb(frame_bgr), frame)

    def _fold(self) -> tuple[int, bool, bool | None]:
        dy, wc, screen = 0, False, None
        for e in self._buf:
            typ = e.get("type")
            pkg = e.get("packageName")
            if typ == "scrolled":
                dy += e.get("dy", 0)
            elif typ == "windowChanged" and pkg is not None and pkg != self.package:
                wc = True
            elif typ == "screenOff":
                screen = False
            elif typ == "screenOn":
                screen = True
            if pkg is not None:
                self.package = pkg
        self._buf = []
        return dy, wc, screen

    def on_thumb(self, th: np.ndarray, frame: dict) -> list[dict]:
        t = frame["tMs"]
        dy, wc, screen = self._fold()
        self.dy_since_ref += dy
        w, h, sw = frame["width"], frame["height"], frame["screenWidth"]
        res = ch.detect(th, self.ref, ch.shift_rows(self.dy_since_ref, w, h, sw), self.cp)
        revealed = None
        if res.revealed_rows is not None:
            r0, r1 = res.revealed_rows
            # the ignored status/nav rows are still screen: a strip touching the band edge
            # extends to the screen edge so content entering under the bar is covered
            if r0 <= self.cp.ignore_top_rows:
                r0 = 0
            if r1 >= ch.THUMB_H - self.cp.ignore_bottom_rows:
                r1 = ch.THUMB_H
            revealed = ch.thumb_box_to_screen((0, r0, ch.THUMB_W, r1), frame)
        changed = ch.thumb_box_to_screen(res.changed_box, frame) if res.changed_box else None
        busy = t < self.busy_until
        tick = sc.Tick(
            t_ms=t, frame_id=frame["frameId"], screen_w=sw, screen_h=frame["screenHeight"],
            changed_tiles=res.changed_tiles, scene_cut=res.scene_cut, revealed_rect=revealed,
            changed_rect=changed, scroll_dy=dy, window_changed=wc, package=self.package,
            screen_on=screen, busy=busy,
        )  # fmt: skip
        before = self.state.skipped
        self.state, req = sc.step(self.state, tick, self.mp)
        if req is not None:
            self.ref = th
            self.dy_since_ref = 0
            self.busy_until = t + self.look_ms
        elif self.ref is None:
            self.ref = th
        fid = frame["frameId"]
        change = {
            "kind": "change", "frameId": fid, "tMs": t, "changedTiles": res.changed_tiles,
            "sceneCut": res.scene_cut, "score": res.score,
            "x": {"revealedRows": list(res.revealed_rows) if res.revealed_rows else None,
                  "shiftRows": res.shift_rows},
        }  # fmt: skip
        look = {
            "kind": "look", "frameId": fid, "tMs": t, "look": req is not None,
            "reason": req.why if req else ("busy" if self.state.skipped > before else "none"),
            "state": self.state.phase,
            "x": {"queue": len(self.queue), "skipped": self.state.skipped},
        }  # fmt: skip
        if req is not None:
            look["rect"] = req.rect
            look["x"]["deadlineMs"] = req.deadline_ms
        return [change, look]


def run_tape(tape_in: Path, mode: str, params: dict | None = None, look_ms: int = 0) -> list[dict]:
    """Replay a tape-in through the pipeline without decoding video."""
    pipe = None
    header = None
    out: list[dict] = []
    for line in Path(tape_in).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        k = r["kind"]
        if k == "header":
            header = r
            pipe = GatekeeperPipeline(mode, params, look_ms)
        elif k == "event":
            pipe.on_event(r["event"])
        elif k == "frame":
            th = np.frombuffer(base64.b64decode(r["thumb"]), np.uint8).reshape(
                ch.THUMB_H, ch.THUMB_W
            )
            frame = {
                "frameId": r["frameId"], "tMs": r["tMs"], "width": header["width"],
                "height": header["height"], "screenWidth": header["screenWidth"],
                "screenHeight": header["screenHeight"],
            }  # fmt: skip
            out.extend(pipe.on_thumb(th, frame))
    return out


def main(argv: list[str] | None = None) -> int:
    from workshop.replay.player import replay

    p = argparse.ArgumentParser(prog="python -m workshop.twin.gatekeeper")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("replay")
    r.add_argument("session")
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--mode", default="balanced")
    r.add_argument("--look-ms", type=int, default=0)
    a = p.parse_args(argv)
    res = replay(Path(a.session), GatekeeperPipeline(a.mode, None, a.look_ms), a.out, video=False)
    print(res.tape_in, res.tape_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
