"""Validate Njord review-needed detection from fixture snapshots."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys


def assert_true(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


REPO_ROOT = Path(__file__).resolve().parents[1]
AGENT_ROOT = REPO_ROOT / "agents" / "njord"
if str(AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_ROOT))

from review import review_snapshot  # noqa: E402
from snapshot import build_snapshot  # noqa: E402


snapshot = build_snapshot(
    plan_id="plan-1",
    plan_name="Household",
    accounts=[
        {
            "id": "account-1",
            "name": "Checking",
            "type": "checking",
            "balance": 1000000,
            "cleared_balance": 1000000,
            "uncleared_balance": 0,
            "on_budget": True,
            "closed": False,
        }
    ],
    categories=[],
    category_groups=[
        {
            "id": "group-1",
            "name": "Everyday",
            "hidden": False,
            "categories": [
                {
                    "id": "category-negative",
                    "name": "Dining",
                    "category_group_id": "group-1",
                    "category_group_name": "Everyday",
                    "budgeted": 50000,
                    "activity": -10000,
                    "balance": -20000,
                    "hidden": False,
                },
                {
                    "id": "category-underfunded",
                    "name": "Coffee",
                    "category_group_id": "group-1",
                    "category_group_name": "Everyday",
                    "budgeted": 0,
                    "activity": -25000,
                    "balance": 0,
                    "hidden": False,
                },
                {
                    "id": "category-delta",
                    "name": "Groceries",
                    "category_group_id": "group-1",
                    "category_group_name": "Everyday",
                    "budgeted": 100000,
                    "activity": -140000,
                    "balance": 10000,
                    "hidden": False,
                },
                {
                    "id": "category-hidden",
                    "name": "Hidden Overspend",
                    "category_group_id": "group-1",
                    "category_group_name": "Everyday",
                    "budgeted": 0,
                    "activity": -30000,
                    "balance": -30000,
                    "hidden": True,
                },
            ],
        }
    ],
    months=[
        {
            "month": "2026-05-01",
            "income": 600000,
            "budgeted": 500000,
            "activity": -450000,
            "to_be_budgeted": 100000,
        }
    ],
    transactions=[
        {
            "id": "transaction-normal",
            "date": "2026-05-10",
            "amount": -10000,
            "payee_name": "Corner Store",
            "category_id": "category-negative",
            "category_name": "Dining",
            "account_id": "account-1",
            "account_name": "Checking",
            "cleared": "cleared",
            "approved": True,
        },
        {
            "id": "transaction-large",
            "date": "2026-05-11",
            "amount": -700000,
            "payee_name": "Annual Insurance",
            "category_id": "category-delta",
            "category_name": "Groceries",
            "account_id": "account-1",
            "account_name": "Checking",
            "cleared": "cleared",
            "approved": True,
        },
        {
            "id": "transaction-uncategorized",
            "date": "2026-05-12",
            "amount": -25000,
            "payee_name": "Mystery Payee",
            "category_id": "",
            "category_name": "",
            "account_id": "account-1",
            "account_name": "Checking",
            "cleared": "uncleared",
            "approved": False,
        },
    ],
    scheduled_transactions=[
        {
            "id": "scheduled-stale",
            "date_first": "2026-01-01",
            "date_next": "2026-05-01",
            "frequency": "monthly",
            "amount": -120000,
            "payee_name": "Rent",
            "category_id": "category-rent",
            "category_name": "Housing",
            "account_id": "account-1",
            "account_name": "Checking",
        }
    ],
    fetched_at=datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc),
)

summary = review_snapshot(snapshot)
rule_ids = {flag.rule_id for flag in summary.flags}

expected_rules = {
    "negative-category-balance",
    "underfunded-category-activity",
    "category-activity-over-budget",
    "uncategorized-transaction",
    "unusually-large-transaction",
    "stale-scheduled-transaction",
}

assert_true(expected_rules.issubset(rule_ids), f"Missing review rules: {expected_rules - rule_ids}")
assert_true(
    not any(flag.subject_id == "category-hidden" for flag in summary.flags),
    "Hidden categories should not produce review flags.",
)

for flag in summary.flags:
    assert_true(flag.detail, f"{flag.rule_id} did not include a neutral explanation.")
    assert_true(flag.evidence, f"{flag.rule_id} did not include supporting evidence.")
    assert_true(flag.confidence in {"low", "medium", "high"}, "Unexpected confidence value.")
    assert_true(flag.severity in {"low", "medium", "high"}, "Unexpected severity value.")

serialized = summary.to_dict()
assert_true(
    any(item["rule_id"] == "stale-scheduled-transaction" for item in serialized["flags"]),
    "Review summary serialization lost stale scheduled transaction flag.",
)

text = str(serialized).lower()
assert_true("bad" not in text and "irresponsible" not in text, "Review language became judgmental.")

print("Njord review validation passed.")
