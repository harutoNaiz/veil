"""Convert between Label Studio and ScreenLabel v1.0.

Command line (exit 0 ok, 2 bad input)::

    python -m workshop.labels.ls_convert to-ls --screens DIR --url-prefix P \
        [--prelabels FILE] --out tasks.json
    python -m workshop.labels.ls_convert from-ls --export ls.json --screens DIR \
        --labeller ID [--accept-predictions] --out labels.json
    python -m workshop.labels.ls_convert check-config
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from jsonschema.exceptions import ValidationError
from PIL import Image

from workshop.contracts.validate import validate

CONTRACT_VERSION = "1.0"
# Label Studio rectangle label -> (concept, default kind, tag)
LABELS: dict[str, tuple[str, str, str | None]] = {
    "cats": ("cats", "photo", None),
    "cat-emoji": ("cats", "emoji", "cat-emoji"),
    "cat-text": ("cats", "text", "cat-text"),
    "spiders": ("spiders", "photo", None),
    "spider-emoji": ("spiders", "emoji", "spider-emoji"),
}
KINDS = ("photo", "cartoon", "drawing", "sticker", "emoji", "text", "other")
SCOPES = ("object", "wholeElement")
LOOKALIKES = ("dog", "fox", "lion", "tiger", "stuffed-toy", "cat-logo", "crab", "other")
APPS = ("instagram", "youtube", "chrome", "whatsapp", "x", "reddit")
META_KEYS = ("app", "surface", "mode", "orientation", "source")
CONFIG_PATH = Path(__file__).with_name("ls_config.xml")


class InputError(Exception):
    """Bad input; the CLI prints the message and exits 2."""


def png_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as im:
        return im.size


def read_meta(screens: Path, stem: str) -> dict:
    side = screens / f"{stem}.json"
    if not side.is_file():
        raise InputError(f"{stem}.png: sidecar {side.name} missing")
    data = json.loads(side.read_text(encoding="utf-8"))
    missing = [k for k in META_KEYS if k not in data]
    if missing:
        raise InputError(f"{side.name}: missing keys {missing}")
    return {k: data[k] for k in META_KEYS}


def label_for(concept: str, tag: str | None) -> str | None:
    """Rectangle label for a box (by concept and tag); None if the concept is unknown."""
    fallback = None
    for name, (c, _kind, t) in LABELS.items():
        if c != concept:
            continue
        if t == tag:
            return name
        if t is None:
            fallback = name
    return fallback


# ---------------------------------------------------------------- to-ls


def _pct(value: float, total: int) -> float:
    return round(value / total * 100, 6)


def _box_results(n: int, label: str, rect: dict, size: tuple[int, int], kind, scope) -> list:
    w, h = size
    rid = f"r{n}"
    out = [
        {
            "id": rid,
            "type": "rectanglelabels",
            "from_name": "box",
            "to_name": "image",
            "original_width": w,
            "original_height": h,
            "image_rotation": 0,
            "value": {
                "x": _pct(rect["x"], w),
                "y": _pct(rect["y"], h),
                "width": _pct(rect["w"], w),
                "height": _pct(rect["h"], h),
                "rotation": 0,
                "rectanglelabels": [label],
            },
        }
    ]
    for name, choice in (("kind", kind), ("scope", scope)):
        if choice:
            out.append(
                {
                    "id": rid,
                    "type": "choices",
                    "from_name": name,
                    "to_name": "image",
                    "value": {"choices": [choice]},
                }
            )
    return out


def _image_choice(name: str, choices: list[str]) -> dict:
    return {
        "type": "choices",
        "from_name": name,
        "to_name": "image",
        "value": {"choices": choices},
    }


def _prelabel_results(entries: list[dict], size: tuple[int, int], is_findings: bool) -> list:
    results: list[dict] = []
    n = 0
    for entry in entries:
        if is_findings:
            if entry.get("decision") != "hide":
                continue
            label = label_for(entry["conceptId"], None)
            boxes = [(label, entry["rect"], None, entry.get("scope"))]
        else:
            boxes = [
                (label_for(b["concept"], b.get("tag")), b["rect"], b.get("kind"), b.get("scope"))
                for b in entry["boxes"]
            ]
        for label, rect, kind, scope in boxes:
            if label is None:
                continue
            n += 1
            results += _box_results(n, label, rect, size, kind, scope)
        if not is_findings:
            if entry.get("clean"):
                results.append(_image_choice("clean", ["clean"]))
            if entry.get("lookalikes"):
                results.append(_image_choice("lookalikes", list(entry["lookalikes"])))
    return results


def to_ls(screens: Path, url_prefix: str, prelabels: list[dict] | None = None) -> list[dict]:
    """One task per PNG; prelabels (ScreenLabel or Finding array) become predictions."""
    is_findings = bool(prelabels) and "findingId" in prelabels[0]
    by_image: dict[str, list[dict]] = {}
    for entry in prelabels or []:
        by_image.setdefault(entry.get("image", ""), []).append(entry)
    tasks = []
    for png in sorted(screens.glob("*.png")):
        task: dict = {"data": {"image": url_prefix + png.name, "name": png.name}}
        if png.name in by_image:
            result = _prelabel_results(by_image[png.name], png_size(png), is_findings)
            task["predictions"] = [{"model_version": "prelabel", "result": result}]
        tasks.append(task)
    return tasks


# ---------------------------------------------------------------- from-ls


def parse_result(result: list[dict], size: tuple[int, int], name: str, problems: list[str]):
    """Return (boxes, clean_ticked, lookalikes) from one Label Studio result list."""
    w, h = size
    rects: list[tuple[str, dict]] = []
    region_choice: dict[str, dict[str, str]] = {}
    clean = False
    lookalikes: list[str] = []
    for idx, res in enumerate(result):
        kind = res.get("type")
        value = res.get("value", {})
        rid = str(res.get("id", f"#{idx}"))
        if kind == "rectanglelabels":
            rects.append((rid, value))
        elif kind == "choices":
            choices = value.get("choices", [])
            field = res.get("from_name")
            if field in ("kind", "scope") and choices:
                region_choice.setdefault(rid, {})[field] = choices[0]
            elif field == "clean":
                clean = "clean" in choices
            elif field == "lookalikes":
                lookalikes += [c for c in choices if c not in lookalikes]
    boxes = []
    for rid, value in rects:
        labels = value.get("rectanglelabels") or []
        if not labels or labels[0] not in LABELS:
            problems.append(f"{name}: unknown rectangle label {labels}")
            continue
        concept, default_kind, tag = LABELS[labels[0]]
        picked = region_choice.get(rid, {})
        box_kind = picked.get("kind", default_kind)
        box_scope = picked.get("scope", "object")
        if box_kind not in KINDS or box_scope not in SCOPES:
            problems.append(f"{name}: bad kind/scope {box_kind}/{box_scope}")
            continue
        rect = {
            "x": round(value["x"] / 100 * w),
            "y": round(value["y"] / 100 * h),
            "w": max(1, round(value["width"] / 100 * w)),
            "h": max(1, round(value["height"] / 100 * h)),
        }
        box = {"rect": rect, "concept": concept, "kind": box_kind}
        if tag:
            box["tag"] = tag
        box["scope"] = box_scope
        boxes.append(box)
    return boxes, clean, lookalikes


def _task_result(task: dict, accept_predictions: bool) -> list[dict] | None:
    annotations = [a for a in task.get("annotations") or [] if not a.get("was_cancelled")]
    if annotations:
        return annotations[-1].get("result", [])
    if accept_predictions and task.get("predictions"):
        return task["predictions"][-1].get("result", [])
    return None


def from_ls(
    export: list[dict], screens: Path, labeller: str, accept_predictions: bool = False
) -> list[dict]:
    """ScreenLabel list (sorted by image); raises InputError listing every bad image."""
    problems: list[str] = []
    labels = []
    for task in export:
        name = (task.get("data") or {}).get("name")
        png = screens / str(name)
        if not name or not png.is_file():
            problems.append(f"{name}: no PNG in {screens}")
            continue
        result = _task_result(task, accept_predictions)
        size = png_size(png)
        boxes, clean, lookalikes = parse_result(result or [], size, name, problems)
        if (boxes and clean) or (not boxes and not clean):
            problems.append(f"{name}: unlabelled or contradictory")
            continue
        label = {
            "contractVersion": CONTRACT_VERSION,
            "image": name,
            "width": size[0],
            "height": size[1],
            "clean": not boxes,
            "boxes": boxes,
            "lookalikes": lookalikes,
            "meta": read_meta(screens, png.stem),
            "labeller": labeller,
        }
        try:
            validate("ScreenLabel", label)
        except ValidationError as exc:
            problems.append(f"{name}: invalid ScreenLabel: {exc.message}")
            continue
        labels.append(label)
    if problems:
        raise InputError("\n".join(problems))
    return sorted(labels, key=lambda x: x["image"])


# ---------------------------------------------------------------- config


def config_problems() -> list[str]:
    """Differences between ls_config.xml and the constants above (empty = identical)."""
    root = ET.parse(CONFIG_PATH).getroot()
    found: dict[str, list[str]] = {}
    for el in root.iter("RectangleLabels"):
        found["box"] = [x.get("value") for x in el.iter("Label")]
    for el in root.iter("Choices"):
        found[el.get("name")] = [x.get("value") for x in el.iter("Choice")]
    want = {
        "box": list(LABELS),
        "kind": list(KINDS),
        "scope": list(SCOPES),
        "clean": ["clean"],
        "lookalikes": list(LOOKALIKES),
    }
    return [
        f"{k}: config {found.get(k)} != constants {v}" for k, v in want.items() if found.get(k) != v
    ]


# ---------------------------------------------------------------- CLI


def _load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InputError(f"cannot read {path}: {exc}") from exc


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m workshop.labels.ls_convert")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("to-ls")
    a.add_argument("--screens", type=Path, required=True)
    a.add_argument("--url-prefix", required=True)
    a.add_argument("--prelabels", type=Path)
    a.add_argument("--out", type=Path, required=True)
    b = sub.add_parser("from-ls")
    b.add_argument("--export", type=Path, required=True)
    b.add_argument("--screens", type=Path, required=True)
    b.add_argument("--labeller", required=True)
    b.add_argument("--accept-predictions", action="store_true")
    b.add_argument("--out", type=Path, required=True)
    sub.add_parser("check-config")
    args = p.parse_args(argv)
    try:
        if args.cmd == "check-config":
            problems = config_problems()
            print("\n".join(problems) if problems else "LS CONFIG OK")
            return 1 if problems else 0
        if args.cmd == "to-ls":
            pre = _load(args.prelabels) if args.prelabels else None
            tasks = to_ls(args.screens, args.url_prefix, pre)
            _write(args.out, tasks)
            print(f"wrote {len(tasks)} tasks to {args.out}")
        else:
            labels = from_ls(
                _load(args.export), args.screens, args.labeller, args.accept_predictions
            )
            _write(args.out, labels)
            print(f"wrote {len(labels)} labels to {args.out}")
    except InputError as exc:
        print(exc, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
