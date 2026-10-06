"""Phone-replay set: PHONE10 words, a replay session of their screens, and the AutoCal pipeline."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

from workshop.replay.pipeline import _plan_record
from workshop.replay.player import _VideoOut
from workshop.twin import judge
from workshop.twin.bench import fmt
from workshop.twin.pieces import crop, make_pieces

SID = "bench-phone"
FPS = 2
T0 = 1000
CATS = ("animal", "object", "food", "vehicle")


def phone10(manifest: dict, words: list[str] | None = None) -> list[str]:
    """Test words round-robin by category (animal, object, food, vehicle, ...), first 10."""
    test = [w for w in manifest["words"] if w.get("split") == "test"]
    if words is not None:
        test = [w for w in test if w["word"] in words]
    cats = list(CATS) + sorted({w["category"] for w in test} - set(CATS))
    queues = [[w["word"] for w in test if w["category"] == c] for c in cats]
    out: list[str] = []
    for k in range(max((len(q) for q in queues), default=0)):
        out += [q[k] for q in queues if k < len(q)]
    return out[:10]


def pick_screens(manifest: dict, words: list[str]) -> list[int]:
    """Every screen with a positive card for `words`, plus the first 100 screens with none."""
    pos = {im["id"] for im in manifest["images"] if set(im.get("pos", [])) & set(words)}
    hit = [s["i"] for s in manifest["screens"] if pos & set(s["cards"])]
    none = [s["i"] for s in manifest["screens"] if not pos & set(s["cards"])][:100]
    return sorted(hit + none)


def _default_render(screen: dict, photos: list[Image.Image]) -> Image.Image:
    from workshop.twin.bench import compose

    img, _, _ = compose.render_feed(compose.screen_rng(screen["i"]), photos, screen["dark"])
    return img


def build(dir: Path, words: list[str] | None = None, render=None) -> Path:
    """Write `<dir>/replay/` (session, empty events, mp4, replay-truth.json); returns session."""
    dir = Path(dir)
    b = fmt.load_bench(dir)
    render = render or _default_render
    names = phone10(b.manifest, words)
    idx = pick_screens(b.manifest, names)
    by_i = {s["i"]: s for s in b.manifest["screens"]}
    out = dir / "replay"
    out.mkdir(parents=True, exist_ok=True)
    vid = _VideoOut(out / f"{SID}.mp4", 360, 780, FPS)
    for i in idx:
        s = by_i[i]
        photos = [Image.open(dir / "cache" / f"{c}.jpg").convert("RGB") for c in s["cards"]]
        img = render(s, photos).convert("RGB")
        vid.write(np.asarray(img)[:, :, ::-1])
    vid.close()
    sess = {
        "sessionVersion": "1", "sessionId": SID, "video": f"{SID}.mp4", "fps": FPS,
        "frameCount": len(idx), "t0Ms": T0, "width": 360, "height": 780, "screenWidth": 360,
        "screenHeight": 780, "scroll": "none", "source": "bench", "packageName": "com.veil.bench",
        "situations": {},
    }  # fmt: skip
    (out / f"{SID}.events.jsonl").write_text("", encoding="utf-8")
    path = out / f"{SID}.session.json"
    path.write_text(json.dumps(sess), encoding="utf-8")
    truth = {"phone10": names, "frames": {str(f): i for f, i in enumerate(idx)}}
    (out / "replay-truth.json").write_text(json.dumps(truth), encoding="utf-8")
    return path


class AutoCalPipeline:
    """Per frame: make_pieces -> embed -> judge each word's cc -> hide rects (screen px)."""

    name = "autocal-v1"

    def __init__(self, ccs: dict[str, dict], desc, mode: str = "balanced") -> None:
        self.ccs, self.desc, self.mode = ccs, desc, mode

    def on_event(self, event: dict) -> list[dict]:
        return []

    def on_frame(self, frame_bgr: np.ndarray, frame: dict) -> list[dict]:
        img = Image.fromarray(np.ascontiguousarray(frame_bgr[:, :, ::-1]))
        regions = make_pieces(img)
        vecs = self.desc.embed_images([crop(img, r["rect"]) for r in regions])
        k = frame["screenWidth"] / frame["width"]
        rects, words = [], []
        for word, cc in self.ccs.items():
            for r, v in zip(regions, judge.judge(vecs, cc, self.mode), strict=True):
                if v["decision"] == "hide":
                    q = r["rect"]
                    rects.append({n: int(round(q[n] * k)) for n in ("x", "y", "w", "h")})
                    words.append(word)
        rec = _plan_record(frame, rects, "look", {})
        for m, w in zip(rec["plan"]["masks"], words, strict=True):
            m["conceptIds"] = [w]
        return [rec]
