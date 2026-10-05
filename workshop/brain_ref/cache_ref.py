"""5.1.1 reference: FingerprintCache op sequence golden (2000 seeded put/get/clear ops)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from workshop.twin import cache

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "guard" / "brain" / "src" / "test" / "resources" / "cache-golden.json"
CAP = 40


def build() -> dict:
    rng = np.random.default_rng(52)
    c = cache.FingerprintCache(capacity=CAP)
    pool = [int(x) for x in rng.integers(0, 2**63, size=30, dtype=np.int64)]
    ops = []
    t = 0
    n_put = 0
    for _ in range(2000):
        t += int(rng.integers(0, 4000))
        kind = rng.choice(["put", "get", "get", "clear"], p=[0.4, 0.3, 0.29, 0.01])
        h = pool[int(rng.integers(0, len(pool)))]
        for b in rng.integers(0, 64, size=int(rng.integers(0, 14))):
            h ^= 1 << int(b)
        w, hh = int(rng.integers(90, 111)), int(rng.integers(90, 111))
        use_sig = bool(rng.random() < 0.5)
        thumb = rng.integers(100, 130, size=(8, 8, 3), dtype=np.uint8)
        sig = (thumb, w, hh) if use_sig else None
        op = {"op": str(kind), "h": h, "t": t}
        if use_sig:
            op["sig"] = {"thumb": thumb.flatten().tolist(), "w": w, "h": hh}
        if kind == "put":
            n_put += 1
            op["fp"] = float(n_put)
            c.put(h, np.array([n_put], dtype=np.float32), t, sig)
        elif kind == "get":
            got = c.get(h, t, sig)
            op["expect"] = None if got is None else float(got[0])
        else:
            c.clear()
        ops.append(op)
    return {"capacity": CAP, "ops": ops, "hits": c.hits, "misses": c.misses}


def main() -> None:
    OUT.write_text(json.dumps(build(), indent=0, sort_keys=True) + "\n", encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
