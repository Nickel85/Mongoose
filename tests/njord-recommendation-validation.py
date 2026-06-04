"""Validate Njord deterministic recommendation generation."""

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

from recommendations import generate_recommendations  # noqa: E402
from review import review_snapshot  # noqa: E402
from snapshot import build_snapshot  # noqa: E402
from spending import review_spending  # noqa: E402


snapshot = build_snapshot(
    plan_id="plan-1",
    plan_name="Household",
    accounts=[
        {
            "id": "account-1",
            "name": "Checking",
            "type": "checking",
            "balance": 500000,
            "cleared_balance": 500000,
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
                    "activity": -140000,
                    "balance": -90000,
                    "hidden": False,
                },
                {
                    "id": "category-coffee",
                    "name": "Coffee",
                    "budgeted": 0,
                    "activity": -30000,
                    "balance": 0,
                    "hidden": False,
                },
            ],
        }
    ],
    months=[
        {
            "month": "2026-05-01",
            "income": 100000,
            "budgeted": 500000,
            "activity": -700000,
            "to_be_budgeted": 0,
        }
    ],
    transactions=[
        {
            "id": "income-1",
            "date": "2026-05-01",
            "amount": 100000,
            "payee_name": "Employer",
            "category_id": "income",
            "category_name": "Inflow",
            "account_id": "account-1",
            "account_name": "Checking",
            "cleared": "cleared",
            "approved": True,
        },
        {
            "id": "large-1",
            "date": "2026-05-02",
            "amount": -600000,
            "payee_name": "Annual Insurance",
            "category_id": "category-dining",
            "category_name": "Dining",
            "account_id": "account-1",
            "account_name": "Checking",
            "cleared": "cleared",
            "approved": True,
        },
        {
            "id": "uncategorized-1",
            "date": "2026-05-03",
            "amount": -30000,
            "payee_name": "Unknown",
            "category_id": "",
            "category_name": "",
            "account_id": "account-1",
            "account_name": "Checking",
            "cleared": "uncleared",
            "approved": False,
        },
        {
            "id": "coffee-1",
            "date": "2026-05-04",
            "amount": -30000,
            "payee_name": "Coffee Shop",
            "category_id": "category-coffee",
            "category_name": "Coffee",
            "account_id": "account-1",
            "account_name": "Checking",
            "cleared": "cleared",
            "approved": True,
        },
    ],
    scheduled_transactions=[
        {
            "id": "scheduled-stale",
            "date_first": "2026-01-01",
            "date_next": "2026-04-01",
            "frequency": "monthly",
            "amount": -100000,
            "payee_name": "Subscription",
            "category_id": "category-dining",
            "category_name": "Dining",
            "account_id": "account-1",
            "account_name": "Checking",
        }
    ],
    fetched_at=datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc),
)

review = review_snapshot(snapshot, as_of=date(2026, 5, 15))
spending = review_spending(snapshot, as_of=date(2026, 5, 15))
summary = generate_recommendations(review, spending)
recommendations = {recommendation.id: recommendation for recommendation in summary.recommendations}

expected_ids = {
    "review-negative-category-balances",
    "review-unfunded-spending",
    "review-category-activity-over-budget",
    "categorize-open-transactions",
    "confirm-large-outflows",
    "review-stale-scheduled-transactions",
    "review-largest-spending-category",
    "review-negative-period-cash-flow",
}

assert_true(
    expected_ids.issubset(set(recommendations)),
    f"Missing recommendation(s): {expected_ids - set(recommendations)}",
)

for recommendation in summary.recommendations:
    assert_true(recommendation.facts, f"{recommendation.id} has no facts.")
    assert_true(recommendation.interpretation, f"{recommendation.id} has no interpretation.")
    assert_true(recommendation.recommendation, f"{recommendation.id} has no recommendation.")
    assert_true(recommendation.expected_impact, f"{recommendation.id} has no expected impact.")
    assert_true(recommendation.evidence, f"{recommendation.id} has no evidence.")
    assert_true(recommendation.risks, f"{recommendation.id} has no risks/tradeoffs.")
    assert_true(
        recommendation.confidence in {"low", "medium", "high"},
        f"{recommendation.id} has unexpected confidence.",
    )

serialized = summary.to_dict()
text = str(serialized).lower()
assert_true("move money now" not in text, "Recommendation implied automatic budget writes.")
assert_true("irresponsible" not in text, "Recommendation language became judgmental.")

print("Njord recommendation validation passed.")
