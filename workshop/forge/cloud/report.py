"""Render docs/reports/ch3-profile.md from out/*.json."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).parent
REPO = HERE.parent.parent.parent
OUT_MD = REPO / "docs" / "reports" / "ch3-profile.md"
HUB = "https://app.aihub.qualcomm.com/jobs/{}/"


def link(job: str | None, text: object, live: bool) -> str:
    if not job:
        return str(text)
    url = HUB.format(job) if live else f"fixture://{job}"
    return f"[{text}]({url})"


def _load(out: Path, name: str) -> dict | None:
    p = out / name
    return json.loads(p.read_text()) if p.is_file() else None


def render(out: Path) -> str:
    prof, prec, bud = (_load(out, n) for n in ("profile.json", "precision.json", "budget.json"))
    src = next((d["source"] for d in (prof, prec, bud) if d), "pending")
    live = src == "live"
    tag = "" if live else " (fixture)"
    lines = [f"# Chapter 3 profile on cloud phones{tag}", "", f"Source: {src}", ""]
    lines += ["## Per-model profile", ""]
    if prof:
        lines += [
            "| Model | Precision | Batch | Latency ms | Peak MB | NPU share | Off-chip | Jobs |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for m in prof["models"]:
            j = m["profileJob"]
            off = "; ".join(f"{o['layer']} ({o['op']}, {o['cause']})" for o in m["offChip"])
            jobs = ", ".join(
                link(x, k, live)
                for k, x in (
                    ("compile", m["compileJob"]),
                    ("profile", j),
                    ("quantize", m["quantizeJob"]),
                )
                if x
            )
            lines.append(
                f"| {m['modelId']} | {m['precision']} | {m['batch']}"
                f" | {link(j, m['latencyMs'], live)} | {link(j, m['peakMemMb'], live)}"
                f" | {link(j, m['npuShare'], live)} | {off or 'none'} | {jobs} |"
            )
    else:
        lines.append("pending")
    lines += ["", "## Precision", ""]
    if prec:
        lines += [
            "| Model | Float score | Chosen | Chosen score | Delta | Latency ms |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for m in prec["models"]:
            c = next((x for x in m["candidates"] if x["precision"] == m["chosen"]), None)
            j = c["inferenceJob"] if c else None
            lines.append(
                f"| {m['modelId']} | {link(j, m['float']['score'], live)} | {m['chosen']}"
                f" | {link(j, c['score'] if c else 'n/a', live)} | {link(j, m['delta'], live)}"
                f" | {link(j, c['latencyMs'] if c else m['float']['latencyMs'], live)} |"
            )
    else:
        lines.append("pending")
    lines += ["", "## Budget (Balanced)", ""]
    if bud:
        lines += ["| Step | ms | Job |", "| --- | --- | --- |"]
        for r in bud["rows"]:
            lines.append(
                f"| {r['step']} | {link(r['job'], r['ms'], live)} | {r['job'] or 'estimated'} |"
            )
        lines.append(
            f"| Total (limit {bud['limitMs']} ms, pass={bud['pass']}) | {bud['totalMs']} | sum |"
        )
        lines += ["", "## Modes", "", "| Mode | Total ms | Pass |", "| --- | --- | --- |"]
        for n, md in bud["modes"].items():
            lines.append(f"| {n} | {md['totalMs']} | {md['pass']} |")
        lines += ["", "Note: YOLOE only exists in size 26s, so Light and Strict reuse it."]
    else:
        lines.append("pending")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "out"))
    ap.add_argument("--dest", default=str(OUT_MD))
    a = ap.parse_args(argv)
    dest = Path(a.dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(render(Path(a.out)), encoding="utf-8")
    print(f"report written to {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
