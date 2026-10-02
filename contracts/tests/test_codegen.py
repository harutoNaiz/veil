"""workshop/contracts/models.py is exactly what the generator makes from the schemas."""

from __future__ import annotations

import subprocess
import sys

from workshop.contracts.validate import REPO_ROOT


def test_models_up_to_date():
    script = REPO_ROOT / "contracts" / "scripts" / "gen_python.py"
    result = subprocess.run(
        [sys.executable, str(script), "--check"], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr
