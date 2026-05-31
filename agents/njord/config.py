"""Shared configuration helpers for Njord."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


AGENT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = AGENT_ROOT.parents[1]
CONFIG_FILE_NAME = "config.json"
CONFIG_ENV_VAR = "MIDAS_CONFIG_PATH"
YNAB_TOKEN_KEY = "YNAB_ACCESS_TOKEN"
YNAB_BUDGET_ID_KEY = "YNAB_BUDGET_ID"


class ConfigFileError(RuntimeError):
    """Raised when the user-local config file cannot be parsed safely."""


def user_config_path() -> Path:
    override = os.environ.get(CONFIG_ENV_VAR, "").strip()
    if override:
        return Path(override).expanduser()

    local_app_data = os.environ.get("LOCALAPPDATA", "").strip()
    if local_app_data:
        return Path(local_app_data) / "Agents" / "Njord" / CONFIG_FILE_NAME

    return Path.home() / ".config" / "agents" / "njord" / CONFIG_FILE_NAME


def load_user_config(config_path: Path | None = None) -> dict[str, str]:
    path = config_path or user_config_path()
    if not path.exists():
        return {}

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigFileError(f"Could not parse Njord config file at {path}.") from exc

    if not isinstance(raw, dict):
        raise ConfigFileError(f"Njord config file at {path} must contain a JSON object.")

    return {
        str(key): str(value).strip()
        for key, value in raw.items()
        if value is not None and str(value).strip()
    }


def load_dotenv(dotenv_path: Path | None = None) -> None:
    if os.environ.get("MIDAS_DISABLE_DOTENV", "").strip() == "1":
        return

    path = dotenv_path or REPO_ROOT / ".env"
    for key, value in read_dotenv(path).items():
        if key and key not in os.environ:
            os.environ[key] = value


def read_dotenv(dotenv_path: Path | None = None) -> dict[str, str]:
    if os.environ.get("MIDAS_DISABLE_DOTENV", "").strip() == "1":
        return {}

    path = dotenv_path or REPO_ROOT / ".env"
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        cleaned_line = line.strip()
        if not cleaned_line or cleaned_line.startswith("#") or "=" not in cleaned_line:
            continue

        key, value = cleaned_line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value

    return values


def env_value(name: str) -> str:
    load_dotenv()
    return os.environ.get(name, "").strip()


def configured_value(name: str) -> str:
    explicit_env_value = os.environ.get(name, "").strip()
    if explicit_env_value:
        return explicit_env_value

    user_config = load_user_config()
    config_value = user_config.get(name, "").strip()
    if config_value:
        return config_value

    return read_dotenv().get(name, "").strip()


def value_source(name: str) -> str:
    if os.environ.get(name, "").strip():
        return "environment"

    try:
        user_config = load_user_config()
    except ConfigFileError:
        return "user config error"

    if user_config.get(name, "").strip():
        return str(user_config_path())

    if read_dotenv().get(name, "").strip():
        return str(REPO_ROOT / ".env")

    return "not configured"


def redacted_presence(value: str) -> str:
    return "configured" if value.strip() else "missing"


def ynab_access_token() -> str:
    return configured_value(YNAB_TOKEN_KEY)


def ynab_budget_id() -> str:
    return configured_value(YNAB_BUDGET_ID_KEY)


def config_status_lines(
    token: str,
    budget_id: str,
    token_source: str,
    budget_source: str,
    config_path: Path | None = None,
    extra_lines: list[str] | None = None,
) -> list[str]:
    path = config_path or user_config_path()
    lines = [
        "Njord configuration status",
        f"Preferred config file: {path}",
        f"YNAB access token: {redacted_presence(token)} ({token_source})",
        f"YNAB budget/plan ID: {redacted_presence(budget_id)} ({budget_source})",
    ]
    if extra_lines:
        lines.extend(extra_lines)
    return lines


def current_config_snapshot() -> dict[str, Any]:
    return {
        "config_path": user_config_path(),
        "token": ynab_access_token(),
        "budget_id": ynab_budget_id(),
        "token_source": value_source(YNAB_TOKEN_KEY),
        "budget_source": value_source(YNAB_BUDGET_ID_KEY),
    }


