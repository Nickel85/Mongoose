"""Validate the Njord write safety design contract."""

from __future__ import annotations

from pathlib import Path
import re


def assert_true(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


REPO_ROOT = Path(__file__).resolve().parents[1]
SAFETY_DOC = REPO_ROOT / "agents" / "njord" / "write-safety.md"
YNAB_API = REPO_ROOT / "agents" / "njord" / "ynab_api.py"

text = SAFETY_DOC.read_text(encoding="utf-8")
lower_text = text.lower()

required_phrases = [
    "natural-language requests must never mutate ynab directly",
    "draft recommendation",
    "proposed write plan",
    "approved plan",
    "executed write",
    "reconciliation record",
    "category budget adjustment",
    "money movement between categories",
    "new-money allocation",
    "transaction category update",
    "transaction memo update",
    "scheduled transaction update",
    "account metadata update",
    "approval record schema",
    "audit record schema",
    "reconciliation record schema",
    "idempotency",
    "prohibited automatic operations",
    "must not include access tokens",
]

for phrase in required_phrases:
    assert_true(phrase in lower_text, f"Safety design is missing: {phrase}")

gate_start = lower_text.find("## implementation gate for later issues")
assert_true(gate_start >= 0, "Implementation gate section is missing.")
gate_text = lower_text[gate_start:]

sequence = [
    "read analysis",
    "proposed write plan",
    "explicit approval",
    "stale-state and policy checks",
    "guarded execution",
    "audit record",
    "reconciliation record",
    "decision outcome metrics",
]
positions = [gate_text.find(item) for item in sequence]
assert_true(all(position >= 0 for position in positions), "Safety sequence is incomplete.")
assert_true(positions == sorted(positions), "Safety sequence is not documented in order.")

for decision in ["approved", "rejected", "edited", "deferred", "expired"]:
    assert_true(decision in lower_text, f"Approval decision is missing: {decision}")

for status in ["success", "partial_success", "drift", "failed", "unknown"]:
    assert_true(status in lower_text, f"Reconciliation status is missing: {status}")

ynab_api_text = YNAB_API.read_text(encoding="utf-8")
mutating_method_pattern = re.compile(r'"(POST|PUT|PATCH|DELETE)"')
assert_true(
    not mutating_method_pattern.search(ynab_api_text),
    "Read-only YNAB API client now contains a mutating HTTP method.",
)

print("Njord write safety validation passed.")
