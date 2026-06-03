"""Period spending analysis for Njord financial snapshots."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from snapshot import FinancialSnapshot, TransactionSnapshot
from ynab_api import parse_iso_date


@dataclass(frozen=True)
class DateRange:
    start: date
    end: date
    label: str

    def contains(self, value: date) -> bool:
        return self.start <= value <= self.end

    def previous(self) -> "DateRange":
        if self.label in {"current month", "previous month"} and self.start.day == 1:
            previous_start = month_start(self.start - timedelta(days=1))
            previous_month_end = next_month_start(previous_start) - timedelta(days=1)
            previous_end_day = min(self.end.day, previous_month_end.day)
            previous_end = date(previous_start.year, previous_start.month, previous_end_day)
            return DateRange(previous_start, previous_end, f"previous {self.label}")

        days = (self.end - self.start).days + 1
        previous_end = self.start - timedelta(days=1)
        previous_start = previous_end - timedelta(days=days - 1)
        return DateRange(previous_start, previous_end, f"previous {self.label}")

    def to_dict(self) -> dict[str, str]:
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "label": self.label,
        }


@dataclass(frozen=True)
class CategorySpend:
    category_id: str
    category_name: str
    outflow: int
    transaction_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NotableTransaction:
    id: str
    date: str
    payee_name: str
    category_name: str
    account_name: str
    amount: int
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PeriodTotals:
    income: int
    outflows: int
    net_cash_flow: int
    transaction_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PeriodComparison:
    previous_range: DateRange
    previous_totals: PeriodTotals
    income_delta: int
    outflow_delta: int
    net_cash_flow_delta: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "previous_range": self.previous_range.to_dict(),
            "previous_totals": self.previous_totals.to_dict(),
            "income_delta": self.income_delta,
            "outflow_delta": self.outflow_delta,
            "net_cash_flow_delta": self.net_cash_flow_delta,
        }


@dataclass(frozen=True)
class SpendingReview:
    period: DateRange
    totals: PeriodTotals
    top_categories: list[CategorySpend] = field(default_factory=list)
    notable_transactions: list[NotableTransaction] = field(default_factory=list)
    comparison: PeriodComparison | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "period": self.period.to_dict(),
            "totals": self.totals.to_dict(),
            "top_categories": [category.to_dict() for category in self.top_categories],
            "notable_transactions": [
                transaction.to_dict() for transaction in self.notable_transactions
            ],
            "comparison": self.comparison.to_dict() if self.comparison else None,
        }


def snapshot_date(snapshot: FinancialSnapshot) -> date:
    try:
        return datetime.fromisoformat(snapshot.metadata.fetched_at).date()
    except ValueError:
        return date.today()


def month_start(value: date) -> date:
    return date(value.year, value.month, 1)


def next_month_start(value: date) -> date:
    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)


def previous_month_range(as_of: date) -> DateRange:
    current_start = month_start(as_of)
    previous_end = current_start - timedelta(days=1)
    previous_start = month_start(previous_end)
    return DateRange(previous_start, previous_end, "previous month")


def current_month_range(as_of: date) -> DateRange:
    return DateRange(month_start(as_of), as_of, "current month")


def explicit_range(start: date, end: date) -> DateRange:
    if end < start:
        raise ValueError("End date must be on or after start date.")
    return DateRange(start, end, "custom range")


def resolve_period(
    snapshot: FinancialSnapshot,
    period: str = "current-month",
    start: date | None = None,
    end: date | None = None,
    as_of: date | None = None,
) -> DateRange:
    if start is not None or end is not None:
        if start is None or end is None:
            raise ValueError("Both start and end dates are required for a custom range.")
        return explicit_range(start, end)

    review_date = as_of or snapshot_date(snapshot)
    if period == "current-month":
        return current_month_range(review_date)
    if period == "previous-month":
        return previous_month_range(review_date)
    raise ValueError("Period must be current-month, previous-month, or a custom range.")


def transaction_date(transaction: TransactionSnapshot) -> date | None:
    return parse_iso_date(transaction.date)


def transactions_in_range(
    transactions: list[TransactionSnapshot],
    date_range: DateRange,
) -> list[TransactionSnapshot]:
    selected: list[TransactionSnapshot] = []
    for transaction in transactions:
        parsed = transaction_date(transaction)
        if parsed is not None and date_range.contains(parsed):
            selected.append(transaction)
    return selected


def calculate_totals(transactions: list[TransactionSnapshot]) -> PeriodTotals:
    income = sum(transaction.amount for transaction in transactions if transaction.amount > 0)
    outflows = sum(abs(transaction.amount) for transaction in transactions if transaction.amount < 0)
    return PeriodTotals(
        income=income,
        outflows=outflows,
        net_cash_flow=income - outflows,
        transaction_count=len(transactions),
    )


def top_spending_categories(
    transactions: list[TransactionSnapshot],
    limit: int = 5,
) -> list[CategorySpend]:
    totals: dict[tuple[str, str], list[int]] = {}
    for transaction in transactions:
        if transaction.amount >= 0:
            continue
        category_id = transaction.category_id or "uncategorized"
        category_name = transaction.category_name or "Uncategorized"
        key = (category_id, category_name)
        if key not in totals:
            totals[key] = [0, 0]
        totals[key][0] += abs(transaction.amount)
        totals[key][1] += 1

    categories = [
        CategorySpend(
            category_id=category_id,
            category_name=category_name,
            outflow=values[0],
            transaction_count=values[1],
        )
        for (category_id, category_name), values in totals.items()
    ]
    return sorted(categories, key=lambda item: (-item.outflow, item.category_name))[:limit]


def notable_transactions(
    transactions: list[TransactionSnapshot],
    limit: int = 5,
) -> list[NotableTransaction]:
    sorted_transactions = sorted(
        transactions,
        key=lambda transaction: (abs(transaction.amount), transaction.date),
        reverse=True,
    )
    notable: list[NotableTransaction] = []
    for transaction in sorted_transactions[:limit]:
        reason = "largest inflow" if transaction.amount > 0 else "largest outflow"
        notable.append(
            NotableTransaction(
                id=transaction.id,
                date=transaction.date,
                payee_name=transaction.payee_name or "Unnamed payee",
                category_name=transaction.category_name or "Uncategorized",
                account_name=transaction.account_name,
                amount=transaction.amount,
                reason=reason,
            )
        )
    return notable


def compare_to_previous_period(
    snapshot: FinancialSnapshot,
    period: DateRange,
    totals: PeriodTotals,
) -> PeriodComparison | None:
    previous = period.previous()
    previous_transactions = transactions_in_range(snapshot.transactions, previous)
    if not previous_transactions:
        return None

    previous_totals = calculate_totals(previous_transactions)
    return PeriodComparison(
        previous_range=previous,
        previous_totals=previous_totals,
        income_delta=totals.income - previous_totals.income,
        outflow_delta=totals.outflows - previous_totals.outflows,
        net_cash_flow_delta=totals.net_cash_flow - previous_totals.net_cash_flow,
    )


def review_spending(
    snapshot: FinancialSnapshot,
    period: str = "current-month",
    start: date | None = None,
    end: date | None = None,
    as_of: date | None = None,
) -> SpendingReview:
    date_range = resolve_period(snapshot, period=period, start=start, end=end, as_of=as_of)
    selected_transactions = transactions_in_range(snapshot.transactions, date_range)
    totals = calculate_totals(selected_transactions)
    return SpendingReview(
        period=date_range,
        totals=totals,
        top_categories=top_spending_categories(selected_transactions),
        notable_transactions=notable_transactions(selected_transactions),
        comparison=compare_to_previous_period(snapshot, date_range, totals),
    )
