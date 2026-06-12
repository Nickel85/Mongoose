"""Validate the Njord REPL session contract."""

from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
NJORD_ROOT = REPO_ROOT / "agents" / "njord"
NJORD_AGENT = NJORD_ROOT / "agent.py"
sys.path.insert(0, str(NJORD_ROOT))

from session import handle_input, run_repl  # noqa: E402


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def ok_output(text: str):
    return lambda: (True, text)


def run_session(script: str, answer=None) -> tuple[int, str, list[str]]:
    calls: list[str] = []

    def answer_request(request: str) -> tuple[bool, str]:
        calls.append(request)
        if answer is not None:
            return answer(request)
        return True, f"routed: {request}"

    output = io.StringIO()
    code = run_repl(
        input_stream=io.StringIO(script),
        output_stream=output,
        color_enabled=False,
        answer_request=answer_request,
        config_status=ok_output("Njord configuration status\nYNAB access token: missing"),
        brief=ok_output("Njord weekly financial brief"),
        budget_summary=ok_output("Njord budget summary"),
        spending_review=ok_output("Njord spending review"),
    )
    return code, output.getvalue(), calls


for exit_command in ("exit", "quit", "/exit", "/quit"):
    exit_code, output, routed = run_session(f"{exit_command}\n")
    assert_true(exit_code == 0, f"{exit_command} did not exit cleanly.")
    assert_true("Njord> " in output, f"{exit_command} did not render the prompt.")
    assert_true(routed == [], f"{exit_command} was unexpectedly routed.")

exit_code, output, routed = run_session("/help\nexit\n")
assert_true(exit_code == 0, "/help session did not exit cleanly.")
for command in ("/help", "/status", "/brief", "/summary", "/spending", "/exit"):
    assert_true(command in output, f"{command} was missing from REPL help.")
assert_true(routed == [], "/help was unexpectedly routed.")

exit_code, output, routed = run_session("/unknown\nexit\n")
assert_true(exit_code == 0, "Unknown slash command session did not exit cleanly.")
assert_true("Unknown session command: /unknown" in output, "Unknown slash command did not fail clearly.")
assert_true(routed == [], "Unknown slash command was unexpectedly routed.")

exit_code, output, routed = run_session("/status\n/brief\n/summary\n/spending\nexit\n")
assert_true(exit_code == 0, "Slash command session did not exit cleanly.")
assert_true("Njord configuration status" in output, "/status did not render status output.")
assert_true("Njord weekly financial brief" in output, "/brief did not render brief output.")
assert_true("Njord budget summary" in output, "/summary did not render summary output.")
assert_true("Njord spending review" in output, "/spending did not render spending output.")
assert_true(routed == [], "Slash commands were unexpectedly routed as natural language.")

exit_code, output, routed = run_session("summarize my current budget\nexit\n")
assert_true(exit_code == 0, "Natural-language session did not exit cleanly.")
assert_true(routed == ["summarize my current budget"], "Natural-language prompt was not routed exactly once.")
assert_true("routed: summarize my current budget" in output, "Natural-language response was not rendered.")

should_exit, events = handle_input(
    "/missing",
    answer_request=lambda request: (_ for _ in ()).throw(AssertionError("unexpected route")),
    config_status=ok_output("status"),
    brief=ok_output("brief"),
    budget_summary=ok_output("summary"),
    spending_review=ok_output("spending"),
)
assert_true(not should_exit, "Unknown slash command should not exit the session.")
assert_true(events[0].kind == "warning", "Unknown slash command should produce a warning event.")

process = subprocess.run(
    [sys.executable, str(NJORD_AGENT), "--no-color"],
    input="exit\n",
    text=True,
    capture_output=True,
    timeout=10,
)
assert_true(process.returncode == 0, f"Njord no-arg REPL failed: {process.stdout}{process.stderr}")
assert_true("Njord> " in process.stdout, "Njord no-arg REPL did not render the prompt.")

process = subprocess.run(
    [sys.executable, str(NJORD_AGENT), "--no-color", "this is a free-form request"],
    text=True,
    capture_output=True,
    timeout=10,
)
assert_true(process.returncode != 2, f"Free-form launcher-style request hit argparse: {process.stderr}")
assert_true("Request: this is a free-form request" in process.stdout, "Free-form request did not route through ask.")

print("Njord REPL validation passed.")
