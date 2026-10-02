"""Motion pipeline (2.3.3): Gatekeeper + oracle detector + Tracker + Planner on the 2.1 player."""

from __future__ import annotations

import argparse
import base64
import dataclasses
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

from workshop.twin import change as ch
from workshop.twin import planner
from workshop.twin.cache import FingerprintCache, phash64, signature, usable
from workshop.twin.gatekeeper import GatekeeperPipeline
from workshop.twin.oracle import DEFAULT_CONCEPTS, OracleDetector, OracleParams, full_sizes
from workshop.twin.tracker import TRACK_MODES, Tracker, covered_pct

MODES = ("light", "balanced", "strict")
NEVER = -(10**9)


def _overlap(r: dict, look: dict) -> int:
    x0, y0 = max(r["x"], look["x"]), max(r["y"], look["y"])
    x1 = min(r["x"] + r["w"], look["x"] + look["w"])
    y1 = min(r["y"] + r["h"], look["y"] + look["h"])
    return max(0, x1 - x0) * max(0, y1 - y0)


class MotionPipeline:
    def __init__(
        self,
        session_json: Path | None,
        mode: str = "balanced",
        *,
        detector: str = "oracle",
        oracle: OracleParams | None = None,
        concepts=DEFAULT_CONCEPTS,
        self_capture_rule: bool = True,
        use_cache: bool = True,
        solid_only: bool = False,
        labels: bool = False,
        hold_mul: int = 1,
        rate_mul: int = 1,
    ) -> None:
        if detector != "oracle":
            raise SystemExit("DEFERRED: real detector path")
        self.name = f"motion-v1-{mode}"
        self.mode = mode
        self.oracle_p = oracle or OracleParams()
        self.solid_only = solid_only
        self.labels = labels
        self.gk = GatekeeperPipeline(mode, look_ms=self.oracle_p.latency_ms)
        if rate_mul != 1:
            self.gk.mp = dataclasses.replace(self.gk.mp, rate=self.gk.mp.rate * rate_mul)
        tp = TRACK_MODES[mode]
        if hold_mul != 1:
            tp = dataclasses.replace(
                tp, hold_ms=tp.hold_ms * hold_mul, max_hold_ms=tp.max_hold_ms * hold_mul
            )
        self.tracker = Tracker(mode, self_capture_rule=self_capture_rule, params=tp)
        self.cache = FingerprintCache() if use_cache else None
        self.oracle = None
        self.truth: dict[int, dict] = {}
        self.sizes: dict[str, tuple[int, int]] = {}
        self.tape_mode = session_json is None
        if session_json is not None:
            sj = Path(session_json)
            sid = json.loads(sj.read_text(encoding="utf-8"))["sessionId"]
            self.oracle = OracleDetector(sj.parent / f"{sid}.truth.jsonl", concepts, self.oracle_p)
            self.truth = self.oracle.truth
            self.sizes = full_sizes(self.truth)
        self.findings_log: list[dict] = []
        self._queue: list[tuple[int, list[dict]]] = []
        self._inbox: list[dict] = []
        self.cum_dy = 0
        self.cum_at: dict[int, int] = {}
        self.look_id = 0
        self.last_start = NEVER
        self._pkg: str | None = None
        self._scrolled = False
        self._appchg = False
        self._last_scroll_t = NEVER
        self._prev_ids: set[int] = set()
        self._prev_reason = "clear"
        self._first = True

    # ---- events
    def on_event(self, event: dict) -> list[dict]:
        self.gk.on_event(event)
        typ, pkg = event.get("type"), event.get("packageName")
        if typ == "scrolled":
            self.tracker.on_scroll(event["dy"], event["tMs"])
            self.cum_dy += event["dy"]
            self._scrolled = True
            self._last_scroll_t = event["tMs"]
        elif typ == "windowChanged" and pkg is not None and pkg != self._pkg:
            self.tracker.on_app_change(event["tMs"])
            self._appchg = True
        elif typ == "screenOff":
            self.tracker.on_screen_off(event["tMs"])
            self._appchg = True
            if self.cache is not None:
                self.cache.clear()
        if pkg is not None:
            self._pkg = pkg
        return []

    # ---- frames
    def on_frame(self, frame_bgr: np.ndarray, frame: dict) -> list[dict]:
        return self._step(ch.thumb(frame_bgr), frame, frame_bgr)

    def _confirm_rect(self, frame: dict) -> dict | None:
        tent = [t for t in self.tracker.tracks if t.state == "tentative"]
        if not tent:
            return None
        sw, sh = frame["screenWidth"], frame["screenHeight"]
        x0 = max(0, min(t.rect["x"] for t in tent) - 20)
        y0 = max(0, min(t.rect["y"] for t in tent) - 20)
        x1 = min(sw, max(t.rect["x"] + t.rect["w"] for t in tent) + 20)
        y1 = min(sh, max(t.rect["y"] + t.rect["h"] for t in tent) + 20)
        if x1 <= x0 or y1 <= y0:
            return None
        return {"x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0}

    def _deliver(self, t: int) -> tuple[list[dict], list[dict]]:
        if self.tape_mode:
            due, self._inbox = self._inbox, []
        else:
            due = [f for dt, fs in self._queue if dt <= t for f in fs]
            self._queue = [(dt, fs) for dt, fs in self._queue if dt > t]
        out = []
        for f in due:
            g = dict(f)
            g["rect"] = dict(f["rect"])
            g["rect"]["y"] += self.cum_dy - self.cum_at.get(f["frameId"], self.cum_dy)
            out.append(g)
        return out, due

    def _step(self, th: np.ndarray, frame: dict, frame_bgr: np.ndarray | None) -> list[dict]:
        t, fid = frame["tMs"], frame["frameId"]
        self.cum_at[fid] = self.cum_dy
        change, look = self.gk.on_thumb(th, frame)
        if change["sceneCut"]:
            self.tracker.on_scene_cut(t)
        if not look["look"]:
            rect = self._confirm_rect(frame)
            gap = self.gk.mp.min_immediate_gap_ms
            if rect is not None and t - self.last_start >= gap and t >= self.gk.busy_until:
                look = dict(look, look=True, reason="periodic", rect=rect)
                look["x"] = dict(look["x"], confirm=True)
                self.gk.busy_until = t + self.oracle_p.latency_ms
        if look["look"]:
            self.last_start = t
            self.look_id += 1
            if not self.tape_mode:
                found = self.oracle.detect(frame, look["rect"], self.look_id)
                if found:
                    self._queue.append((t + self.oracle_p.latency_ms, found))
        shifted, due = self._deliver(t)
        for f in due:
            self.findings_log.append(
                {"kind": "finding", "tMs": t, "finding": f, "x": {"deliverFrameId": fid}}
            )
        self.tracker.on_findings(shifted, t)
        tracks = self.tracker.tick(t, frame.get("ownOverlay", []))
        ids = {x["trackId"] for x in tracks}
        if self._appchg:
            reason = "appChange"
        elif look["look"] or due:
            reason = "look"
        elif self._scrolled:
            reason = "scroll"
        elif self._prev_ids - ids:
            reason = "expire"
        elif not tracks or self._first:
            reason = "clear"
        else:
            reason = self._prev_reason
        self._prev_ids, self._prev_reason, self._first = ids, reason, False
        self._scrolled = self._appchg = False
        plan = planner.plan(
            tracks, t_ms=t, frame_id=fid, screen_w=frame["screenWidth"],
            screen_h=frame["screenHeight"], mode=self.mode, reason=reason,
            labels=self.labels, solid_only=self.solid_only,
        )  # fmt: skip
        recs = [
            change,
            look,
            {"kind": "tracks", "tMs": t, "frameId": fid, "tracks": tracks},
            {"kind": "maskPlan", "tMs": t, "frameId": fid, "plan": plan},
        ]
        if self.cache is not None and frame_bgr is not None and look["look"]:
            recs.append(self._cache_rec(frame, frame_bgr, look["rect"]))
        return recs

    def _situation(self, t: int, fid: int) -> str:
        scene = self.truth.get(fid, {}).get("scene", "")
        if scene in ("feed", "grid") and t - self._last_scroll_t <= 300:
            return "feedScroll"
        return scene if scene in ("reels", "video") else "static"

    def _cache_rec(self, frame: dict, img: np.ndarray, look_rect: dict) -> dict:
        t, fid = frame["tMs"], frame["frameId"]
        h0, m0 = self.cache.hits, self.cache.misses
        own = frame.get("ownOverlay", [])
        sc = img.shape[1] / frame["screenWidth"]
        for b in sorted(self.truth.get(fid, {"boxes": []})["boxes"], key=lambda b: b["key"]):
            r = b["rect"]
            fw, fh = self.sizes[b["key"]]
            if _overlap(r, look_rect) * 2 < fw * fh or covered_pct(r, own) >= 50:
                continue
            x0, y0 = int(r["x"] * sc), int(r["y"] * sc)
            x1, y1 = int((r["x"] + r["w"]) * sc), int((r["y"] + r["h"]) * sc)
            crop = img[max(0, y0) : y1, max(0, x0) : x1]
            if crop.size == 0 or not usable(crop):
                continue
            h = phash64(crop)
            sig = signature(crop)
            if self.cache.get(h, t, sig) is None:
                vec = np.array([(h >> (8 * k)) & 255 for k in range(8)], np.float16) / 255
                self.cache.put(h, vec, t, sig)
        return {
            "kind": "cache", "tMs": t, "frameId": fid, "hits": self.cache.hits - h0,
            "misses": self.cache.misses - m0, "x": {"situation": self._situation(t, fid)},
        }  # fmt: skip


def run_tape(tape_in: Path, mode: str = "balanced", **kw) -> list[dict]:
    kw.setdefault("use_cache", False)
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
            pipe = MotionPipeline(None, mode, **kw)
        elif k == "event":
            pipe.on_event(r["event"])
        elif k == "finding":
            pipe._inbox.append(r["finding"])
        elif k == "frame":
            th = np.frombuffer(base64.b64decode(r["thumb"]), np.uint8).reshape(
                ch.THUMB_H, ch.THUMB_W
            )
            frame = {
                "frameId": r["frameId"], "tMs": r["tMs"], "width": header["width"],
                "height": header["height"], "screenWidth": header["screenWidth"],
                "screenHeight": header["screenHeight"], "ownOverlay": r.get("ownOverlay", []),
            }  # fmt: skip
            out.extend(pipe._step(th, frame, None))
    return out


# ---------------------------------------------------------------- eval CLI
def _sessions(items: list[str]) -> list[Path]:
    out: list[Path] = []
    for it in items:
        p = Path(it)
        out.extend(sorted(p.glob("*.session.json")) if p.is_dir() else [p])
    return out


def _sbs(a: Path, b: Path, out: Path) -> None:
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(a), "-i", str(b), "-filter_complex"]
    cmd += ["hstack", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "30"]
    cmd += ["-pix_fmt", "yuv420p", str(out)]
    subprocess.run(cmd, check=True)


def _pooled(rows: list[dict]) -> dict:
    from workshop.eval.score_motion import percentile

    ttc = sorted(x for r in rows for x in r["ttc_list"])
    cov_n = sum(r["cov_frames"] for r in rows)
    vis_n = sum(r["vis_frames"] for r in rows)
    glue = sorted(x for r in rows for x in r["glue_list"])
    clean = sum(r["clean_min"] for r in rows)
    frames = sum(r["frames"] for r in rows)
    looks = sum(r["looks"] for r in rows)
    rec = [r["recover_max_ms"] for r in rows if r["recover_max_ms"] is not None]
    return {
        "appearances": len(ttc),
        "ttc_median_ms": percentile(ttc, 50) if ttc else 0,
        "ttc_p95_ms": percentile(ttc, 95) if ttc else 0,
        "coverage_pct": round(100 * cov_n / vis_n, 2) if vis_n else 100.0,
        "flicker": sum(r["flicker"] for r in rows),
        "wrong_covers": sum(r["wrong_covers"] for r in rows),
        "wrong_per_min": round(sum(r["wrong_covers"] for r in rows) / clean, 3) if clean else 0.0,
        "clean_min": round(clean, 3),
        "glue_median_px": glue[len(glue) // 2] if glue else 0,
        "analysed_pct": round(100 * looks / frames, 2) if frames else 0.0,
        "recover_max_ms": max(rec) if rec else None,
        "frames": frames,
    }


def _gate(b: dict, per_session: dict) -> dict:
    ac = {
        "AC-2.3-01": (b["ttc_p95_ms"] <= 300, f"p95={b['ttc_p95_ms']}ms"),
        "AC-2.3-02": (
            all(s["flicker"] == 0 for s in per_session.values()),
            "flicker=" + ",".join(f"{k}:{s['flicker']}" for k, s in per_session.items()),
        ),
        "AC-2.3-03": (b["wrong_per_min"] <= 1, f"{b['wrong_per_min']}/min"),
        "AC-2.3-04": (b["coverage_pct"] >= 95, f"{b['coverage_pct']}%"),
        "AC-2.3-05": (b["glue_median_px"] <= 8, f"{b['glue_median_px']}px"),
    }
    gate = (
        b["ttc_p95_ms"] <= 300
        and b["flicker"] == 0
        and b["wrong_per_min"] < 1
        and b["analysed_pct"] < 15
    )
    return {"ac": {k: [v[0], v[1]] for k, v in ac.items()}, "gate": gate}


def cmd_eval(a) -> int:
    from workshop.eval.score_motion import score
    from workshop.replay.player import replay

    modes = [m for m in a.modes.split(",") if m]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    sessions = _sessions(a.sessions)
    kw = {"self_capture_rule": a.rule == "on", "solid_only": a.solid_only or a.fallback}
    if a.fallback:
        kw.update(hold_mul=2, rate_mul=2)
    result: dict = {"modes": {}, "options": {**kw, "detector": a.detector}}
    for mode in modes:
        per: dict[str, dict] = {}
        for sj in sessions:
            sid = json.loads(sj.read_text(encoding="utf-8"))["sessionId"]
            video = mode == "balanced" and a.video == "balanced"
            pipe = MotionPipeline(sj, mode, detector=a.detector, **kw)
            d = out / mode
            res = replay(sj, pipe, d, self_capture=True, markers=False, video=video)
            lp = sj.parent / "labels" / f"{sid}.json"
            label = json.loads(lp.read_text(encoding="utf-8")) if lp.exists() else None
            per[sid] = score(sj, res.tape_out, label)
            if video and res.video:
                _sbs(sj.parent / f"{sid}.mp4", res.video, d / f"{sid}.sbs.mp4")
        agg = _pooled(list(per.values()))
        sit: dict = {}
        for r in per.values():
            for k, v in r["cache"]["situation"].items():
                s = sit.setdefault(k, {"hits": 0, "misses": 0})
                s["hits"] += v["hits"]
                s["misses"] += v["misses"]
        for s in sit.values():
            n = s["hits"] + s["misses"]
            s["hit_pct"] = round(100 * s["hits"] / n, 1) if n else 0.0
        agg["cache"] = sit
        result["modes"][mode] = {"sessions": per, "aggregate": agg}
        print(f"MODE {mode}: " + json.dumps({k: v for k, v in agg.items() if k != "cache"}))
    if "balanced" in result["modes"]:
        b = result["modes"]["balanced"]
        g = _gate(b["aggregate"], b["sessions"])
        for k, (ok, val) in g["ac"].items():
            print(f"{k}: {'PASS' if ok else 'FAIL'} {val}")
        label = "ch2 (synthetic, fallback)" if a.fallback else "ch2 (synthetic)"
        print(f"GATE {label}: {'PASS' if g['gate'] else 'FAIL'}")
        result["gate"] = {"name": label, "pass": g["gate"], "ac": g["ac"]}
    (out / "scores.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m workshop.twin.motion")
    sub = p.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("eval")
    e.add_argument("--sessions", nargs="+", required=True)
    e.add_argument("--out", required=True)
    e.add_argument("--modes", default="light,balanced,strict")
    e.add_argument("--rule", choices=["on", "off"], default="on")
    e.add_argument("--detector", choices=["oracle", "real"], default="oracle")
    e.add_argument("--solid-only", action="store_true")
    e.add_argument("--fallback", action="store_true")
    e.add_argument("--video", choices=["balanced", "none"], default="balanced")
    r = sub.add_parser("report")
    r.add_argument("--scores", required=True)
    r.add_argument("--torture", default=None)
    r.add_argument("--fallback-scores", default=None)
    a = p.parse_args(argv)
    if a.cmd == "eval":
        return cmd_eval(a)
    from workshop.eval.score_motion import write_report

    write_report(a.scores, a.torture, a.fallback_scores)
    return 0


if __name__ == "__main__":
    sys.exit(main())
