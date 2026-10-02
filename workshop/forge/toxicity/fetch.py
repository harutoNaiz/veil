"""Pick an Apache-2.0 multilingual toxicity classifier and a small labelled sample."""

from __future__ import annotations

import json
import os

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

from huggingface_hub import HfApi, snapshot_download  # noqa: E402

from workshop.forge.common import FORGE_DATA  # noqa: E402

OUT = FORGE_DATA / "toxicity"
CHOICE = OUT / "choice.json"
MAX_ROWS = 1000


def _licence(info) -> str:
    for t in info.tags or []:
        if t.startswith("license:"):
            return t.split(":", 1)[1]
    return ""


def pick_model(api: HfApi) -> dict:
    cands = []
    for q in ("mmbert toxicity", "multilingual toxicity", "toxic multilingual classifier"):
        for m in api.list_models(search=q, sort="downloads", limit=30):
            cands.append(m.id)
    seen = []
    for mid in dict.fromkeys(cands):
        info = api.model_info(mid)
        lic = _licence(info)
        small = ("mmbert" in mid.lower() and "small" in mid.lower()) or "mmbert" in mid.lower()
        if lic == "apache-2.0" and "text-classification" == (info.pipeline_tag or ""):
            seen.append((0 if small else 1, mid, info))
    if not seen:
        raise SystemExit("no Apache-2.0 toxicity classifier found")
    seen.sort(key=lambda t: t[0])
    _, mid, info = seen[0]
    return {
        "id": mid,
        "url": f"https://huggingface.co/{mid}",
        "licence": "Apache-2.0",
        "revision": info.sha,
    }


def pick_sample(api: HfApi) -> dict | None:
    for q in ("toxicity multilingual", "toxic comments multilingual", "jigsaw multilingual"):
        for d in api.list_datasets(search=q, sort="downloads", limit=20):
            info = api.dataset_info(d.id)
            if _licence(info) in (
                "apache-2.0",
                "cc0-1.0",
                "mit",
                "cc-by-4.0",
                "cc-by-sa-4.0",
                "cc-by-3.0",
            ):
                return {
                    "id": d.id,
                    "url": f"https://huggingface.co/datasets/{d.id}",
                    "licence": _licence(info),
                }
    return None


def _read_rows(path: str):
    import csv

    if path.endswith(".parquet"):
        import polars as pl  # already in the env (transitive); no new dependency

        df = pl.read_parquet(path)
        yield from df[:: max(1, df.height // MAX_ROWS)].iter_rows(named=True)
    elif path.endswith((".jsonl", ".json")):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip().rstrip(",")
                if line.startswith("{"):
                    yield json.loads(line)
    else:
        with open(path, encoding="utf-8", newline="") as f:
            yield from csv.DictReader(f, delimiter=chr(9) if path.endswith(".tsv") else ",")


def write_sample(ds: dict) -> int:
    """Download one small csv/tsv/jsonl file; keep <= MAX_ROWS rows. Prints counts only."""
    from huggingface_hub import hf_hub_download

    info = HfApi().dataset_info(ds["id"], files_metadata=True)
    files = [
        s
        for s in info.siblings or []
        if s.rfilename.endswith((".csv", ".tsv", ".jsonl", ".parquet"))
        and 0 < (s.size or 0) < 60_000_000
    ]
    files.sort(key=lambda s: s.size)
    for sib in files:
        path = hf_hub_download(ds["id"], sib.rfilename, repo_type="dataset")
        rows = []
        for r in _read_rows(path):
            text = next((r[k] for k in ("text", "comment_text", "content") if k in r), None)
            lab = next((r[k] for k in ("toxic", "label", "toxicity") if k in r), None)
            try:
                rows.append({"text": text, "label": int(float(lab) >= 0.5)})
            except (TypeError, ValueError):
                continue
            if len(rows) >= MAX_ROWS:
                break
        if len({r["label"] for r in rows}) == 2:
            with open(OUT / "sample.jsonl", "w", encoding="utf-8") as f:
                for r in rows:
                    f.write(json.dumps(r, ensure_ascii=False) + chr(10))
            ds["file"] = sib.rfilename
            return len(rows)
    return 0


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    api = HfApi()
    model = pick_model(api)
    snapshot_download(model["id"])
    ds = pick_sample(api)
    n = write_sample(ds) if ds else 0
    CHOICE.write_text(
        json.dumps({"model": model, "dataset": ds, "rows": n}, indent=1), encoding="utf-8"
    )
    print("model", model["id"], model["licence"], "dataset", ds and ds["id"], "rows", n)


if __name__ == "__main__":
    main()
