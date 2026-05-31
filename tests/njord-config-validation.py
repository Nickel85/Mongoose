"""Validate Njord YNAB configuration handling without live API calls."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path


def assert_true(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


REPO_ROOT = Path(__file__).resolve().parents[1]
AGENT_ROOT = REPO_ROOT / "agents" / "njord"
if str(AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_ROOT))

os.environ["MIDAS_DISABLE_DOTENV"] = "1"
os.environ.pop("YNAB_ACCESS_TOKEN", None)
os.environ.pop("YNAB_BUDGET_ID", None)

import agent  # noqa: E402
from config import (  # noqa: E402
    YNAB_BUDGET_ID_KEY,
    YNAB_TOKEN_KEY,
    current_config_snapshot,
    load_user_config,
)
from router import route_request  # noqa: E402
from ynab_api import YnabResourceResult  # noqa: E402


class FakeYnabClient:
    plans: list[dict[str, str]] = [{"id": "plan-1", "name": "Household"}]
    ok: bool = True
    message: str = "YNAB API request succeeded."
    status_code: int | None = 200
    seen_tokens: list[str] = []

    def __init__(self, token: str) -> None:
        self.seen_tokens.append(token)

    def list_plans(self) -> YnabResourceResult:
        return YnabResourceResult(
            ok=self.ok,
            items=self.plans,
            message=self.message,
            status_code=self.status_code,
        )


def with_config_file(payload: dict[str, str] | None) -> Path:
    temp_dir = Path(tempfile.mkdtemp(prefix="njord-config-validation-"))
    config_path = temp_dir / "config.json"
    os.environ["MIDAS_CONFIG_PATH"] = str(config_path)
    if payload is not None:
        config_path.write_text(json.dumps(payload), encoding="utf-8")
    return config_path


agent.YnabClient = FakeYnabClient

missing_path = with_config_file(None)
missing_ok, missing_output = agent.run_config_status()
assert_true(not missing_ok, "Missing token unexpectedly passed config status.")
assert_true("YNAB access token: missing" in missing_output, "Missing token was not reported.")
assert_true(str(missing_path) in missing_output, "Preferred config path was not reported.")

config_path = with_config_file(
    {
        YNAB_TOKEN_KEY: "secret-token",
        YNAB_BUDGET_ID_KEY: "plan-1",
    }
)
loaded = load_user_config(config_path)
assert_true(loaded[YNAB_TOKEN_KEY] == "secret-token", "User config token was not loaded.")

snapshot = current_config_snapshot()
assert_true(snapshot["token"] == "secret-token", "Configured token was not resolved.")
assert_true(snapshot["budget_id"] == "plan-1", "Configured budget ID was not resolved.")
assert_true(snapshot["token_source"] == str(config_path), "Token source did not prefer user config.")

ok, output = agent.run_config_status()
assert_true(ok, output)
assert_true("YNAB access token: configured" in output, "Configured token was not reported.")
assert_true("budget/plan ID matches" in output, "Budget ID was not validated.")
assert_true("secret-token" not in output, "Config status leaked the access token.")

with_config_file(
    {
        YNAB_TOKEN_KEY: "secret-token",
        YNAB_BUDGET_ID_KEY: "missing-plan",
    }
)
invalid_ok, invalid_output = agent.run_config_status()
assert_true(not invalid_ok, "Invalid configured budget ID unexpectedly passed.")
assert_true("did not match" in invalid_output, "Invalid budget ID was not actionable.")
assert_true("secret-token" not in invalid_output, "Invalid status leaked the access token.")

route = route_request("config status")
assert_true(route.capability == "config-status", "Installed config status request was not routed.")

print("YNAB config validation passed.")

