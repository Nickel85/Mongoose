"""Validate terminal color behavior for Mongoose and Njord."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def assert_true(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


REPO_ROOT = Path(__file__).resolve().parents[1]
MONGOOSE_CLI = REPO_ROOT / "mongoose" / "mongoose.py"
NJORD_AGENT = REPO_ROOT / "agents" / "njord" / "agent.py"
ESC = "\033["


def run_command(command: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged_env = {**os.environ, **(env or {})}
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        env=merged_env,
    )


plain_state = run_command([sys.executable, str(MONGOOSE_CLI), "state"])
assert_true(plain_state.returncode == 0, plain_state.stderr)
assert_true("Mongoose local state" in plain_state.stdout, "Plain state output lost heading text.")
assert_true(ESC not in plain_state.stdout, "Redirected Mongoose output should not include ANSI color by default.")

forced_state = run_command(
    [sys.executable, str(MONGOOSE_CLI), "state"],
    env={"MONGOOSE_FORCE_COLOR": "1"},
)
assert_true(forced_state.returncode == 0, forced_state.stderr)
assert_true(ESC in forced_state.stdout, "Mongoose forced color output did not include ANSI color.")

no_color_state = run_command(
    [sys.executable, str(MONGOOSE_CLI), "--no-color", "state"],
    env={"MONGOOSE_FORCE_COLOR": "1"},
)
assert_true(no_color_state.returncode == 0, no_color_state.stderr)
assert_true(ESC not in no_color_state.stdout, "Mongoose --no-color did not suppress forced color.")

plain_njord = run_command([sys.executable, str(NJORD_AGENT), "ask", "hello"])
assert_true("Request: hello" in plain_njord.stdout, "Plain Njord output lost request text.")
assert_true(ESC not in plain_njord.stdout, "Redirected Njord output should not include ANSI color by default.")

forced_njord = run_command(
    [sys.executable, str(NJORD_AGENT), "ask", "hello"],
    env={"NJORD_FORCE_COLOR": "1"},
)
assert_true(ESC in forced_njord.stdout, "Njord forced color output did not include ANSI color.")

no_color_njord = run_command(
    [sys.executable, str(NJORD_AGENT), "--no-color", "ask", "hello"],
    env={"NJORD_FORCE_COLOR": "1"},
)
assert_true(ESC not in no_color_njord.stdout, "Njord --no-color did not suppress forced color.")

print("Terminal output validation passed.")
