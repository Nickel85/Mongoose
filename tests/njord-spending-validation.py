"""Validate Njord period spending review from fixture snapshots."""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
import sys


def assert_true(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


REPO_ROOT = Path(__file__).resolve().parents[1]
AGENT_ROOT = REPO_ROOT / "agents" / "njord"
if str(AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_ROOT))

from router import route_request  # noqa: E402
from snapshot import build_snapshot  # noqa: E402
from spending import review_spending  # noqa: E402
from ynab_api import format_currency  # noqa: E402


snapshot = build_snapshot(
    plan_id="plan-1",
    plan_name="Household",
    accounts=[
        {
            "id": "account-1",
            "name": "Checking",
            "type": "checking",
            "balance": 1200000,
            "cleared_balance": 1200000,
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
                    "id": "category-groceries",
                    "name": "Groceries",
                    "budgeted": 300000,
                    "activity": -165000,
                    "balance": 135000,
                    "hidden": False,
                },
                {
                    "id": "category-dining",
                    "name": "Dining",
                    "budgeted": 100000,
                    "activity": -70000,
                    "balance": 30000,
                    "hidden": False,
                },
            ],
        }
    ],
    months=[
        {
            "month": "2026-04-01",
            "income": 550000,
            "budgeted": 500000,
            "activity": -260000,
            "to_be_budgeted": 50000,
        },
        {
            "month": "2026-05-01",
            "income": 600000,
            "budgeted": 550000,
            "activity": -235000,
            "to_be_budgeted": 50000,
        },
    ],
    transactions=[
        {
            "id": "income-may",
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
            "id": "groceries-1",
            "date": "2026-05-05",
            "amount": -125000,
            "payee_name": "Market",
            "category_id": "category-groceries",
            "category_name": "Groceries",
            "account_id": "account-1",
            "account_name": "Checking",
            "cleared": "cleared",
            "approved": True,
        },
        {
            "id": "dining-1",
            "date": "2026-05-10",
            "amount": -70000,
            "payee_name": "Cafe",
            "category_id": "category-dining",
            "category_name": "Dining",
            "account_id": "account-1",
            "account_name": "Checking",
            "cleared": "cleared",
            "approved": True,
        },
        {
            "id": "uncategorized-1",
            "date": "2026-05-12",
            "amount": -40000,
            "payee_name": "Unknown",
            "category_id": "",
            "category_name": "",
            "account_id": "account-1",
            "account_name": "Checking",
            "cleared": "uncleared",
            "approved": False,
        },
        {
            "id": "income-april",
            "date": "2026-04-01",
            "amount": 550000,
            "payee_name": "Employer",
            "category_id": "income",
            "category_name": "Inflow",
            "account_id": "account-1",
            "account_name": "Checking",
            "cleared": "cleared",
            "approved": True,
        },
        {
            "id": "groceries-april",
            "date": "2026-04-03",
            "amount": -150000,
            "payee_name": "Market",
            "category_id": "category-groceries",
            "category_name": "Groceries",
            "account_id": "account-1",
            "account_name": "Checking",
            "cleared": "cleared",
            "approved": True,
        },
        {
            "id": "rent-april",
            "date": "2026-04-04",
            "amount": -110000,
            "payee_name": "Rent",
            "category_id": "category-rent",
            "category_name": "Housing",
            "account_id": "account-1",
            "account_name": "Checking",
            "cleared": "cleared",
            "approved": True,
        },
    ],
    scheduled_transactions=[],
    fetched_at=datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc),
)

current = review_spending(snapshot, period="current-month", as_of=date(2026, 5, 15))
assert_true(current.period.start == date(2026, 5, 1), "Current month start was wrong.")
assert_true(current.period.end == date(2026, 5, 15), "Current month end was wrong.")
assert_true(current.totals.income == 600000, "May income total used wrong milliunits.")
assert_true(current.totals.outflows == 235000, "May outflow total used wrong milliunits.")
assert_true(current.totals.net_cash_flow == 365000, "May net cash flow was wrong.")
assert_true(format_currency(current.totals.outflows) == "$235.00", "Currency conversion was wrong.")
assert_true(current.top_categories[0].category_name == "Groceries", "Top category order was wrong.")
assert_true(current.top_categories[0].outflow == 125000, "Top category outflow was wrong.")
assert_true(
    any(category.category_name == "Uncategorized" for category in current.top_categories),
    "Uncategorized spending was not grouped.",
)
assert_true(current.notable_transactions[0].id == "income-may", "Largest transaction was not notable.")
assert_true(current.comparison is not None, "Current period comparison was missing.")
assert_true(current.comparison.previous_totals.outflows == 260000, "Previous outflows were wrong.")
assert_true(current.comparison.outflow_delta == -25000, "Outflow delta was wrong.")

previous = review_spending(snapshot, period="previous-month", as_of=date(2026, 5, 15))
assert_true(previous.period.start == date(2026, 4, 1), "Previous month start was wrong.")
assert_true(previous.period.end == date(2026, 4, 30), "Previous month end was wrong.")
assert_true(previous.totals.income == 550000, "Previous month income was wrong.")

custom = review_spending(
    snapshot,
    start=date(2026, 5, 5),
    end=date(2026, 5, 10),
)
assert_true(custom.period.label == "custom range", "Custom period label was wrong.")
assert_true(custom.totals.income == 0, "Custom range included income outside the range.")
assert_true(custom.totals.outflows == 195000, "Custom range outflows were wrong.")
assert_true(custom.totals.transaction_count == 2, "Custom range transaction count was wrong.")

serialized = current.to_dict()
assert_true(serialized["period"]["start"] == "2026-05-01", "Serialization lost period start.")
assert_true(serialized["comparison"] is not None, "Serialization lost comparison.")

route = route_request("review my current month spending")
assert_true(route.capability == "ynab-spending-review", "Spending request did not route correctly.")

print("Njord spending validation passed.")
