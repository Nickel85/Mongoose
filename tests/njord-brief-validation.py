"""Validate Njord manual brief composition from fixture snapshots."""

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

from brief import build_brief, render_brief  # noqa: E402
from router import route_request  # noqa: E402
from snapshot import build_snapshot  # noqa: E402


snapshot = build_snapshot(
    plan_id="plan-1",
    plan_name="Household",
    accounts=[
        {
            "id": "account-1",
            "name": "Checking",
            "type": "checking",
            "balance": 900000,
            "cleared_balance": 900000,
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
                    "id": "category-dining",
                    "name": "Dining",
                    "budgeted": 50000,
                    "activity": -130000,
                    "balance": -80000,
                    "hidden": False,
                },
                {
                    "id": "category-groceries",
                    "name": "Groceries",
                    "budgeted": 250000,
                    "activity": -100000,
                    "balance": 150000,
                    "hidden": False,
                },
            ],
        }
    ],
    months=[
        {
            "month": "2026-05-01",
            "income": 600000,
            "budgeted": 500000,
            "activity": -280000,
            "to_be_budgeted": 100000,
        }
    ],
    transactions=[
        {
            "id": "income-1",
            "date": "2026-05-01",
            "amount": 600000,
            "payee_name": "Employer",
            "category_id": "income",
            "category_name": "Inflow",
            "account_id": "account-1",
            "account_name": "Checking",
            "cleared": "cleared",
            "approved": True,
        },
        {
            "id": "dining-1",
            "date": "2026-05-06",
            "amount": -130000,
            "payee_name": "Restaurant",
            "category_id": "category-dining",
            "category_name": "Dining",
            "account_id": "account-1",
            "account_name": "Checking",
            "cleared": "cleared",
            "approved": True,
        },
        {
            "id": "groceries-1",
            "date": "2026-05-07",
            "amount": -100000,
            "payee_name": "Market",
            "category_id": "category-groceries",
            "category_name": "Groceries",
            "account_id": "account-1",
            "account_name": "Checking",
            "cleared": "cleared",
            "approved": True,
        },
        {
            "id": "uncategorized-1",
            "date": "2026-05-08",
            "amount": -50000,
            "payee_name": "Unknown",
            "category_id": "",
            "category_name": "",
            "account_id": "account-1",
            "account_name": "Checking",
            "cleared": "uncleared",
            "approved": False,
        },
    ],
    scheduled_transactions=[],
    fetched_at=datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc),
)

brief = build_brief(snapshot)
output = render_brief(brief)

assert_true("Njord weekly financial brief" in output, "Brief title was missing.")
assert_true("Observations" in output, "Observations section was missing.")
assert_true("Spending highlights" in output, "Spending highlights section was missing.")
assert_true("Notable transactions" in output, "Notable transactions section was missing.")
assert_true("Review items" in output, "Review items section was missing.")
assert_true("Suggested next actions" in output, "Suggested next actions section was missing.")
assert_true("Boundaries" in output, "Boundaries section was missing.")
assert_true("Dining" in output, "Expected category evidence was missing.")
assert_true("read-only" in output.lower(), "Read-only boundary was missing.")
assert_true("does not modify YNAB" in output, "Write-safety boundary was missing.")
assert_true(len(brief.review.flags) > 0, "Brief did not include review flags.")
assert_true(
    len(brief.recommendations.recommendations) > 0,
    "Brief did not include recommended next actions.",
)

serialized = brief.to_dict()
assert_true(
    serialized["recommendations"]["recommendations"],
    "Brief serialization lost recommendations.",
)

route = route_request("Give me a weekly financial brief")
assert_true(route.capability == "brief", "Weekly brief request did not route to brief.")

print("Njord brief validation passed.")
