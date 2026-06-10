"""Validate generated Mongoose architecture artifacts."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MONGOOSE_CLI = REPO_ROOT / "mongoose" / "mongoose.py"


result = subprocess.run(
    [
        sys.executable,
        str(MONGOOSE_CLI),
        "architecture",
        "validate",
        "--root",
        str(REPO_ROOT),
    ],
    cwd=REPO_ROOT,
    check=False,
    text=True,
    capture_output=True,
)

if result.returncode != 0:
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    raise SystemExit(result.returncode)

print(result.stdout, end="")
