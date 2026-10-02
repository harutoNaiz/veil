"""Print the base64 float16 text of a reproducible random unit vector.

Usage: python contracts/scripts/make_vector.py --dim 8 --seed 1
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from workshop.contracts.rules import encode_f16  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dim", type=int, required=True, help="number of vector elements")
    parser.add_argument("--seed", type=int, required=True, help="random seed")
    args = parser.parse_args(argv)
    print(encode_f16(np.random.default_rng(args.seed).standard_normal(args.dim)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
