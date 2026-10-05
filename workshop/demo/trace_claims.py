"""Check that demo docs cite the final report, name every licensed part and cover the script."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

APPENDIX_C = [
    "SigLIP2",
    "YOLOE (Ultralytics)",
    "MobileCLIP / MobileCLIP2 weights",
    "NudeNet",
    "Toxicity model",
]
NUMBER = re.compile(r"\d(?:\.\d+)?\s?(?:%|ms|s|GB|MB|fps|/s)(?![A-Za-z])")
CITE = re.compile(r"\[(F-\d{2})\]")
ROW = re.compile(r"^\|\s*(F-\d{2})\s*\|")
STEP = re.compile(r"^#{2,4}\s*Step\s+(\d+)\b", re.IGNORECASE)


def report_ids(report: Path) -> set[str]:
    ids = set()
    for line in report.read_text(encoding="utf-8").splitlines():
        m = ROW.match(line.strip())
        if m:
            ids.add(m.group(1))
    return ids


def check_citations(docs: Path, ids: set[str]) -> list[str]:
    bad = []
    for path in sorted(docs.glob("*.md")):
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith("<!-- nocite -->"):
                continue
            cites = CITE.findall(line)
            if NUMBER.search(line) and not cites:
                bad.append(f"{path.name}:{n}: number without [F-NN]: {line.strip()}")
            bad += [f"{path.name}:{n}: unknown id {c}" for c in cites if c not in ids]
    return bad


def check_appendix_c(docs: Path) -> list[str]:
    qa = docs / "qa-sheet.md"
    if not qa.exists():
        return ["qa-sheet.md: missing"]
    text = qa.read_text(encoding="utf-8")
    return [f"qa-sheet.md: missing licence part '{p}'" for p in APPENDIX_C if p not in text]


def check_script(docs: Path) -> list[str]:
    path = docs / "demo-script.md"
    if not path.exists():
        return ["demo-script.md: missing"]
    text = path.read_text(encoding="utf-8")
    steps = {int(m.group(1)) for line in text.splitlines() if (m := STEP.match(line))}
    bad = []
    if steps != set(range(1, 8)):
        bad.append(f"demo-script.md: need steps 1-7, found {sorted(steps)}")
    if "airplane mode" not in text.lower():
        bad.append("demo-script.md: does not mention airplane mode")
    return bad


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--appendix-c", action="store_true")
    a = ap.parse_args(argv)
    docs, report = Path(a.docs), Path(a.report)
    bad = check_citations(docs, report_ids(report))
    if a.appendix_c:
        bad += check_appendix_c(docs)
        bad += check_script(docs)
    for b in bad:
        print(b)
    print("trace_claims:", "FAIL" if bad else "OK")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
