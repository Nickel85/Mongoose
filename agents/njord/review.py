"""Review-needed detection for Njord financial snapshots."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from statistics import median
from typing import Any

from snapshot import FinancialSnapshot
from ynab_api import parse_iso_date


@dataclass(frozen=True)
class ReviewThresholds:
    large_transaction_absolute: int = 500000
    large_transaction_multiplier: float = 3.0
    category_activity_budget_ratio: float = 1.25
    stale_scheduled_days: int = 7


@dataclass(frozen=True)
class ReviewFlag:
    rule_id: str
    title: str
    subject_type: str
    subject_id: str
    subject_name: str
    severity: str
    confidence: str
    amount: int | None
    detail: str
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReviewSummary:
    flags: list[ReviewFlag]

    def by_severity(self, severity: str) -> list[ReviewFlag]:
        return [flag for flag in self.flags if flag.severity == severity]

    def to_dict(self) -> dict[str, Any]:
        return {"flags": [flag.to_dict() for flag in self.flags]}


def snapshot_date(snapshot: FinancialSnapshot) -> date:
    fetched_at = snapshot.metadata.fetched_at
    try:
        return datetime.fromisoformat(fetched_at).date()
    except ValueError:
        return date.today()


def review_snapshot(
    snapshot: FinancialSnapshot,
    thresholds: ReviewThresholds | None = None,
    as_of: date | None = None,
) -> ReviewSummary:
    active_thresholds = thresholds or ReviewThresholds()
    review_date = as_of or snapshot_date(snapshot)
    flags: list[ReviewFlag] = []

    flags.extend(negative_category_flags(snapshot))
    flags.extend(underfunded_category_flags(snapshot))
    flags.extend(category_delta_flags(snapshot, active_thresholds))
    flags.extend(uncategorized_transaction_flags(snapshot))
    flags.extend(large_transaction_flags(snapshot, active_thresholds))
    flags.extend(stale_scheduled_transaction_flags(snapshot, active_thresholds, review_date))

    return ReviewSummary(flags=sorted(flags, key=flag_sort_key))


def flag_sort_key(flag: ReviewFlag) -> tuple[int, str, str]:
    severity_order = {"high": 0, "medium": 1, "low": 2}
    return (
        severity_order.get(flag.severity, 3),
        flag.rule_id,
        flag.subject_name.lower(),
    )


def visible_categories(snapshot: FinancialSnapshot):
    return [category for category in snapshot.categories if not category.hidden]


def negative_category_flags(snapshot: FinancialSnapshot) -> list[ReviewFlag]:
    flags: list[ReviewFlag] = []
    for category in visible_categories(snapshot):
        if category.balance >= 0:
            continue
        flags.append(
            ReviewFlag(
                rule_id="negative-category-balance",
                title="Category balance is negative",
                subject_type="category",
                subject_id=category.id,
                subject_name=category.name or "Unnamed category",
                severity="high" if category.balance <= -100000 else "medium",
                confidence="high",
                amount=category.balance,
                detail=(
                    "This category has a negative available balance and may need "
                    "review or reallocation."
                ),
                evidence={
                    "balance": category.balance,
                    "budgeted": category.budgeted,
                    "activity": category.activity,
                    "group": category.group_name,
                },
            )
        )
    return flags


def underfunded_category_flags(snapshot: FinancialSnapshot) -> list[ReviewFlag]:
    flags: list[ReviewFlag] = []
    for category in visible_categories(snapshot):
        if not (category.budgeted <= 0 and category.activity < 0 and category.balance <= 0):
            continue
        flags.append(
            ReviewFlag(
                rule_id="underfunded-category-activity",
                title="Spending occurred with little or no assigned budget",
                subject_type="category",
                subject_id=category.id,
                subject_name=category.name or "Unnamed category",
                severity="medium",
                confidence="medium",
                amount=category.activity,
                detail=(
                    "This category has outflow activity without assigned budget "
                    "coverage in the loaded snapshot."
                ),
                evidence={
                    "budgeted": category.budgeted,
                    "activity": category.activity,
                    "balance": category.balance,
                    "group": category.group_name,
                },
            )
        )
    return flags


def category_delta_flags(
    snapshot: FinancialSnapshot,
    thresholds: ReviewThresholds,
) -> list[ReviewFlag]:
    flags: list[ReviewFlag] = []
    for category in visible_categories(snapshot):
        activity_outflow = abs(min(category.activity, 0))
        if category.budgeted <= 0 or activity_outflow == 0:
            continue
        trigger_amount = int(category.budgeted * thresholds.category_activity_budget_ratio)
        if activity_outflow < trigger_amount:
            continue
        flags.append(
            ReviewFlag(
                rule_id="category-activity-over-budget",
                title="Category activity is materially above assigned budget",
                subject_type="category",
                subject_id=category.id,
                subject_name=category.name or "Unnamed category",
                severity="high" if activity_outflow >= category.budgeted * 2 else "medium",
                confidence="medium",
                amount=-activity_outflow,
                detail=(
                    "Current outflow activity is materially higher than the "
                    "assigned budget for this category."
                ),
                evidence={
                    "budgeted": category.budgeted,
                    "activity_outflow": activity_outflow,
                    "trigger_amount": trigger_amount,
                    "ratio": thresholds.category_activity_budget_ratio,
                },
            )
        )
    return flags


def uncategorized_transaction_flags(snapshot: FinancialSnapshot) -> list[ReviewFlag]:
    flags: list[ReviewFlag] = []
    for transaction in snapshot.transactions:
        has_category = transaction.category_id or transaction.category_name
        if has_category:
            continue
        flags.append(
            ReviewFlag(
                rule_id="uncategorized-transaction",
                title="Transaction is uncategorized",
                subject_type="transaction",
                subject_id=transaction.id,
                subject_name=transaction.payee_name or "Unnamed transaction",
                severity="medium",
                confidence="high",
                amount=transaction.amount,
                detail="This transaction has no category in the loaded snapshot.",
                evidence={
                    "date": transaction.date,
                    "account": transaction.account_name,
                    "cleared": transaction.cleared,
                    "approved": transaction.approved,
                },
            )
        )
    return flags


def large_transaction_flags(
    snapshot: FinancialSnapshot,
    thresholds: ReviewThresholds,
) -> list[ReviewFlag]:
    outflows = [abs(transaction.amount) for transaction in snapshot.transactions if transaction.amount < 0]
    if not outflows:
        return []

    median_outflow = int(median(outflows))
    trigger_amount = max(
        thresholds.large_transaction_absolute,
        int(median_outflow * thresholds.large_transaction_multiplier),
    )
    flags: list[ReviewFlag] = []

    for transaction in snapshot.transactions:
        amount = abs(transaction.amount)
        if transaction.amount >= 0 or amount < trigger_amount:
            continue
        flags.append(
            ReviewFlag(
                rule_id="unusually-large-transaction",
                title="Transaction is unusually large",
                subject_type="transaction",
                subject_id=transaction.id,
                subject_name=transaction.payee_name or "Unnamed transaction",
                severity="high" if amount >= trigger_amount * 2 else "medium",
                confidence="high" if amount >= trigger_amount * 2 else "medium",
                amount=transaction.amount,
                detail=(
                    "This outflow is large relative to the configured absolute "
                    "threshold and the median loaded outflow."
                ),
                evidence={
                    "date": transaction.date,
                    "category": transaction.category_name,
                    "account": transaction.account_name,
                    "median_outflow": median_outflow,
                    "trigger_amount": trigger_amount,
                },
            )
        )
    return flags


def stale_scheduled_transaction_flags(
    snapshot: FinancialSnapshot,
    thresholds: ReviewThresholds,
    as_of: date,
) -> list[ReviewFlag]:
    flags: list[ReviewFlag] = []
    for transaction in snapshot.scheduled_transactions:
        next_date = parse_iso_date(transaction.date_next)
        if next_date is None:
            continue
        days_overdue = (as_of - next_date).days
        if days_overdue < thresholds.stale_scheduled_days:
            continue
        flags.append(
            ReviewFlag(
                rule_id="stale-scheduled-transaction",
                title="Scheduled transaction date appears stale",
                subject_type="scheduled_transaction",
                subject_id=transaction.id,
                subject_name=transaction.payee_name or "Unnamed scheduled transaction",
                severity="high" if days_overdue >= 30 else "medium",
                confidence="medium",
                amount=transaction.amount,
                detail=(
                    "The next scheduled transaction date is older than the "
                    "snapshot review date."
                ),
                evidence={
                    "date_next": transaction.date_next,
                    "days_overdue": days_overdue,
                    "frequency": transaction.frequency,
                    "account": transaction.account_name,
                    "category": transaction.category_name,
                },
            )
        )
    return flags
