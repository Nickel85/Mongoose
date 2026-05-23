"""Shared configuration helpers for Personal CFO."""

from __future__ import annotations

import os
from pathlib import Path


AGENT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = AGENT_ROOT.parents[1]


def load_dotenv(dotenv_path: Path | None = None) -> None:
    path = dotenv_path or REPO_ROOT / ".env"
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        cleaned_line = line.strip()
        if not cleaned_line or cleaned_line.startswith("#") or "=" not in cleaned_line:
            continue

        key, value = cleaned_line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


def env_value(name: str) -> str:
    load_dotenv()
    return os.environ.get(name, "").strip()


def ynab_access_token() -> str:
    return env_value("YNAB_ACCESS_TOKEN")


def ynab_budget_id() -> str:
    return env_value("YNAB_BUDGET_ID")

