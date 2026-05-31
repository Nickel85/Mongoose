"""Normalized financial snapshot model for Njord."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from ynab_api import YnabClient, YnabResourceResult, parse_iso_date


@dataclass(frozen=True)
class SnapshotMetadata:
    source: str
    plan_id: str
    plan_name: str
    fetched_at: str
    includes: list[str]


@dataclass(frozen=True)
class AccountSnapshot:
    id: str
    name: str
    type: str
    balance: int
    cleared_balance: int
    uncleared_balance: int
    on_budget: bool
    closed: bool


@dataclass(frozen=True)
class CategorySnapshot:
    id: str
    name: str
    group_id: str
    group_name: str
    budgeted: int
    activity: int
    balance: int
    hidden: bool


@dataclass(frozen=True)
class CategoryGroupSnapshot:
    id: str
    name: str
    hidden: bool
    categories: list[CategorySnapshot] = field(default_factory=list)


@dataclass(frozen=True)
class MonthSnapshot:
    month: str
    income: int
    budgeted: int
    activity: int
    to_be_budgeted: int


@dataclass(frozen=True)
class TransactionSnapshot:
    id: str
    date: str
    amount: int
    payee_name: str
    category_id: str
    category_name: str
    account_id: str
    account_name: str
    memo: str
    cleared: str
    approved: bool


@dataclass(frozen=True)
class ScheduledTransactionSnapshot:
    id: str
    date_first: str
    date_next: str
    frequency: str
    amount: int
    payee_name: str
    category_id: str
    category_name: str
    account_id: str
    account_name: str
    memo: str


@dataclass(frozen=True)
class FinancialSnapshot:
    metadata: SnapshotMetadata
    accounts: list[AccountSnapshot]
    category_groups: list[CategoryGroupSnapshot]
    categories: list[CategorySnapshot]
    months: list[MonthSnapshot]
    transactions: list[TransactionSnapshot]
    scheduled_transactions: list[ScheduledTransactionSnapshot]

    def open_on_budget_accounts(self) -> list[AccountSnapshot]:
        return [account for account in self.accounts if account.on_budget and not account.closed]

    def total_on_budget_balance(self) -> int:
        return sum(account.balance for account in self.open_on_budget_accounts())

    def categories_with_balance(self) -> list[CategorySnapshot]:
        return [
            category
            for category in self.categories
            if not category.hidden and category.balance != 0
        ]

    def underfunded_categories(self) -> list[CategorySnapshot]:
        return [
            category
            for category in self.categories
            if not category.hidden and category.balance < 0
        ]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SnapshotResult:
    ok: bool
    snapshot: FinancialSnapshot | None
    message: str


def text_value(raw: dict[str, Any], key: str) -> str:
    value = raw.get(key)
    return str(value).strip() if value is not None else ""


def int_value(raw: dict[str, Any], key: str) -> int:
    value = raw.get(key, 0)
    return value if isinstance(value, int) else 0


def bool_value(raw: dict[str, Any], key: str, default: bool = False) -> bool:
    value = raw.get(key, default)
    return value if isinstance(value, bool) else default


def normalize_accounts(raw_accounts: list[dict[str, Any]]) -> list[AccountSnapshot]:
    return [
        AccountSnapshot(
            id=text_value(account, "id"),
            name=text_value(account, "name"),
            type=text_value(account, "type"),
            balance=int_value(account, "balance"),
            cleared_balance=int_value(account, "cleared_balance"),
            uncleared_balance=int_value(account, "uncleared_balance"),
            on_budget=bool_value(account, "on_budget", True),
            closed=bool_value(account, "closed"),
        )
        for account in raw_accounts
    ]


def category_from_raw(
    category: dict[str, Any],
    group_id: str = "",
    group_name: str = "",
    group_hidden: bool = False,
) -> CategorySnapshot:
    return CategorySnapshot(
        id=text_value(category, "id"),
        name=text_value(category, "name"),
        group_id=text_value(category, "category_group_id") or group_id,
        group_name=text_value(category, "category_group_name") or group_name,
        budgeted=int_value(category, "budgeted"),
        activity=int_value(category, "activity"),
        balance=int_value(category, "balance"),
        hidden=bool_value(category, "hidden", group_hidden),
    )


def normalize_categories(
    raw_categories: list[dict[str, Any]],
    raw_category_groups: list[dict[str, Any]] | None = None,
) -> tuple[list[CategoryGroupSnapshot], list[CategorySnapshot]]:
    groups: list[CategoryGroupSnapshot] = []
    categories: list[CategorySnapshot] = []

    for group in raw_category_groups or []:
        group_id = text_value(group, "id")
        group_name = text_value(group, "name")
        group_hidden = bool_value(group, "hidden")
        group_categories = [
            category_from_raw(category, group_id, group_name, group_hidden)
            for category in group.get("categories", [])
            if isinstance(category, dict)
        ]
        categories.extend(group_categories)
        groups.append(
            CategoryGroupSnapshot(
                id=group_id,
                name=group_name,
                hidden=group_hidden,
                categories=group_categories,
            )
        )

    if raw_categories:
        standalone_categories = [category_from_raw(category) for category in raw_categories]
        categories.extend(standalone_categories)
        known_group_ids = {group.id for group in groups}
        for category in standalone_categories:
            if category.group_id and category.group_id not in known_group_ids:
                groups.append(
                    CategoryGroupSnapshot(
                        id=category.group_id,
                        name=category.group_name,
                        hidden=False,
                        categories=[
                            item
                            for item in standalone_categories
                            if item.group_id == category.group_id
                        ],
                    )
                )
                known_group_ids.add(category.group_id)

    return groups, categories


def normalize_months(raw_months: list[dict[str, Any]]) -> list[MonthSnapshot]:
    return [
        MonthSnapshot(
            month=text_value(month, "month"),
            income=int_value(month, "income"),
            budgeted=int_value(month, "budgeted"),
            activity=int_value(month, "activity"),
            to_be_budgeted=int_value(month, "to_be_budgeted"),
        )
        for month in raw_months
        if parse_iso_date(text_value(month, "month")) is not None
    ]


def normalize_transactions(raw_transactions: list[dict[str, Any]]) -> list[TransactionSnapshot]:
    return [
        TransactionSnapshot(
            id=text_value(transaction, "id"),
            date=text_value(transaction, "date"),
            amount=int_value(transaction, "amount"),
            payee_name=text_value(transaction, "payee_name"),
            category_id=text_value(transaction, "category_id"),
            category_name=text_value(transaction, "category_name"),
            account_id=text_value(transaction, "account_id"),
            account_name=text_value(transaction, "account_name"),
            memo=text_value(transaction, "memo"),
            cleared=text_value(transaction, "cleared"),
            approved=bool_value(transaction, "approved"),
        )
        for transaction in raw_transactions
        if parse_iso_date(text_value(transaction, "date")) is not None
    ]


def normalize_scheduled_transactions(
    raw_scheduled_transactions: list[dict[str, Any]],
) -> list[ScheduledTransactionSnapshot]:
    return [
        ScheduledTransactionSnapshot(
            id=text_value(transaction, "id"),
            date_first=text_value(transaction, "date_first"),
            date_next=text_value(transaction, "date_next"),
            frequency=text_value(transaction, "frequency"),
            amount=int_value(transaction, "amount"),
            payee_name=text_value(transaction, "payee_name"),
            category_id=text_value(transaction, "category_id"),
            category_name=text_value(transaction, "category_name"),
            account_id=text_value(transaction, "account_id"),
            account_name=text_value(transaction, "account_name"),
            memo=text_value(transaction, "memo"),
        )
        for transaction in raw_scheduled_transactions
        if parse_iso_date(text_value(transaction, "date_next")) is not None
    ]


def build_snapshot(
    plan_id: str,
    plan_name: str,
    accounts: list[dict[str, Any]],
    categories: list[dict[str, Any]],
    months: list[dict[str, Any]],
    transactions: list[dict[str, Any]],
    scheduled_transactions: list[dict[str, Any]],
    category_groups: list[dict[str, Any]] | None = None,
    fetched_at: datetime | None = None,
) -> FinancialSnapshot:
    normalized_accounts = normalize_accounts(accounts)
    normalized_category_groups, normalized_categories = normalize_categories(
        categories,
        category_groups,
    )
    timestamp = (fetched_at or datetime.now(timezone.utc)).replace(microsecond=0)
    return FinancialSnapshot(
        metadata=SnapshotMetadata(
            source="ynab",
            plan_id=plan_id,
            plan_name=plan_name,
            fetched_at=timestamp.isoformat(),
            includes=[
                "accounts",
                "category_groups",
                "categories",
                "months",
                "transactions",
                "scheduled_transactions",
            ],
        ),
        accounts=normalized_accounts,
        category_groups=normalized_category_groups,
        categories=normalized_categories,
        months=normalize_months(months),
        transactions=normalize_transactions(transactions),
        scheduled_transactions=normalize_scheduled_transactions(scheduled_transactions),
    )


def failed_resource_message(resource: str, result: YnabResourceResult) -> str:
    return f"Could not load YNAB {resource}: {result.message}"


def load_snapshot(client: YnabClient, plan_id: str, plan_name: str) -> SnapshotResult:
    accounts = client.list_accounts(plan_id)
    if not accounts.ok:
        return SnapshotResult(False, None, failed_resource_message("accounts", accounts))

    categories = client.list_categories(plan_id)
    if not categories.ok:
        return SnapshotResult(False, None, failed_resource_message("categories", categories))

    category_groups = client.list_category_groups(plan_id)
    raw_category_groups = category_groups.items if category_groups.ok else []

    months = client.list_months(plan_id)
    if not months.ok:
        return SnapshotResult(False, None, failed_resource_message("months", months))

    transactions = client.list_transactions(plan_id)
    if not transactions.ok:
        return SnapshotResult(False, None, failed_resource_message("transactions", transactions))

    scheduled_transactions = client.list_scheduled_transactions(plan_id)
    if not scheduled_transactions.ok:
        return SnapshotResult(
            False,
            None,
            failed_resource_message("scheduled transactions", scheduled_transactions),
        )

    snapshot = build_snapshot(
        plan_id=plan_id,
        plan_name=plan_name,
        accounts=accounts.items,
        categories=categories.items,
        category_groups=raw_category_groups,
        months=months.items,
        transactions=transactions.items,
        scheduled_transactions=scheduled_transactions.items,
    )
    return SnapshotResult(True, snapshot, "YNAB snapshot loaded.")
