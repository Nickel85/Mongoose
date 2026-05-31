"""Validate Njord normalized financial snapshot conversion."""

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

from snapshot import build_snapshot, load_snapshot  # noqa: E402
from ynab_api import YnabResourceResult  # noqa: E402


accounts = [
    {
        "id": "account-1",
        "name": "Checking",
        "type": "checking",
        "balance": 125000,
        "cleared_balance": 120000,
        "uncleared_balance": 5000,
        "on_budget": True,
        "closed": False,
        "token": "should-not-survive",
    },
    {
        "id": "account-2",
        "name": "Closed Savings",
        "type": "savings",
        "balance": 50000,
        "on_budget": True,
        "closed": True,
    },
]
category_groups = [
    {
        "id": "group-1",
        "name": "Everyday",
        "hidden": False,
        "categories": [
            {
                "id": "category-1",
                "name": "Groceries",
                "category_group_id": "group-1",
                "category_group_name": "Everyday",
                "budgeted": 300000,
                "activity": -125000,
                "balance": 175000,
                "hidden": False,
                "authorization": "should-not-survive",
            },
            {
                "id": "category-2",
                "name": "Dining",
                "category_group_id": "group-1",
                "category_group_name": "Everyday",
                "budgeted": 50000,
                "activity": -90000,
                "balance": -40000,
                "hidden": False,
            },
        ],
    }
]
months = [
    {
        "month": "2026-05-01",
        "income": 600000,
        "budgeted": 550000,
        "activity": -400000,
        "to_be_budgeted": 50000,
    }
]
transactions = [
    {
        "id": "transaction-1",
        "date": "2026-05-10",
        "amount": -25000,
        "payee_name": "Market",
        "category_id": "category-1",
        "category_name": "Groceries",
        "account_id": "account-1",
        "account_name": "Checking",
        "memo": "weekly shop",
        "cleared": "cleared",
        "approved": True,
        "api_key": "should-not-survive",
    }
]
scheduled_transactions = [
    {
        "id": "scheduled-1",
        "date_first": "2026-05-01",
        "date_next": "2026-06-01",
        "frequency": "monthly",
        "amount": -120000,
        "payee_name": "Rent",
        "category_id": "category-3",
        "category_name": "Housing",
        "account_id": "account-1",
        "account_name": "Checking",
        "memo": "lease",
    }
]

snapshot = build_snapshot(
    plan_id="plan-1",
    plan_name="Household",
    accounts=accounts,
    categories=[],
    category_groups=category_groups,
    months=months,
    transactions=transactions,
    scheduled_transactions=scheduled_transactions,
    fetched_at=datetime(2026, 5, 31, 2, 0, tzinfo=timezone.utc),
)

assert_true(snapshot.metadata.plan_id == "plan-1", "Plan ID was not preserved.")
assert_true(snapshot.metadata.fetched_at == "2026-05-31T02:00:00+00:00", "Freshness timestamp was not serialized.")
assert_true(len(snapshot.category_groups) == 1, "Category group was not normalized.")
assert_true(len(snapshot.categories) == 2, "Nested categories were not flattened.")
assert_true(snapshot.total_on_budget_balance() == 125000, "Closed accounts affected on-budget balance.")
assert_true(len(snapshot.underfunded_categories()) == 1, "Underfunded category was not detected.")
assert_true(len(snapshot.months) == 1, "Month was not normalized.")
assert_true(len(snapshot.transactions) == 1, "Transaction was not normalized.")
assert_true(len(snapshot.scheduled_transactions) == 1, "Scheduled transaction was not normalized.")

serialized = snapshot.to_dict()
serialized_text = str(serialized)
assert_true("should-not-survive" not in serialized_text, "Raw secret-like values leaked into snapshot serialization.")
assert_true("token" not in serialized_text.lower(), "Secret-like key leaked into snapshot serialization.")
assert_true("api_key" not in serialized_text.lower(), "Secret-like key leaked into snapshot serialization.")


class FakeClient:
    def list_accounts(self, _plan_id: str) -> YnabResourceResult:
        return YnabResourceResult(True, accounts, "ok")

    def list_categories(self, _plan_id: str) -> YnabResourceResult:
        return YnabResourceResult(True, [], "ok")

    def list_category_groups(self, _plan_id: str) -> YnabResourceResult:
        return YnabResourceResult(True, category_groups, "ok")

    def list_months(self, _plan_id: str) -> YnabResourceResult:
        return YnabResourceResult(True, months, "ok")

    def list_transactions(self, _plan_id: str) -> YnabResourceResult:
        return YnabResourceResult(True, transactions, "ok")

    def list_scheduled_transactions(self, _plan_id: str) -> YnabResourceResult:
        return YnabResourceResult(True, scheduled_transactions, "ok")


loaded = load_snapshot(FakeClient(), "plan-1", "Household")
assert_true(loaded.ok and loaded.snapshot is not None, loaded.message)
assert_true(loaded.snapshot.metadata.plan_name == "Household", "Loaded snapshot lost plan name.")

print("Njord snapshot validation passed.")
