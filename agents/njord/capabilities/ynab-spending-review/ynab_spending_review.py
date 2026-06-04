"""Read-only YNAB spending review capability for Njord."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import Any


AGENT_ROOT = Path(__file__).resolve().parents[2]
if str(AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_ROOT))

from config import ConfigFileError, current_config_snapshot
from snapshot import load_snapshot
from spending import review_spending
from ynab_api import YnabClient, choose_plan, format_currency, list_plans, parse_iso_date


def configure_output() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def plan_label(plan: dict[str, Any]) -> str:
    return plan.get("name") or plan.get("id") or "selected YNAB plan"


def parse_cli_date(value: str | None, label: str) -> date | None:
    if value is None:
        return None
    parsed = parse_iso_date(value)
    if parsed is None:
        raise ValueError(f"{label} must use YYYY-MM-DD format.")
    return parsed


def load_spending_review(
    period: str = "current-month",
    start: date | None = None,
    end: date | None = None,
) -> tuple[bool, str]:
    try:
        config = current_config_snapshot()
    except ConfigFileError as exc:
        return (
            False,
            "\n".join(
                [
                    str(exc),
                    "Run 'Njord config status' after fixing the configuration file.",
                ]
            ),
        )

    configured_id = config["budget_id"]
    if not config["token"]:
        return (
            False,
            "YNAB_ACCESS_TOKEN is not configured. Run 'Njord config status' for setup details.",
        )

    if not configured_id:
        return (
            False,
            "YNAB_BUDGET_ID is not configured. Run 'Njord config status' to validate available plans.",
        )

    plans_result = list_plans()
    if not plans_result.ok:
        return False, plans_result.message

    plans = plans_result.items
    if not plans:
        return False, "YNAB connection succeeded, but no plans were returned."

    selected_plan = choose_plan(plans, configured_id)
    if selected_plan is None:
        return False, "No YNAB plan could be selected."

    selected_id = selected_plan.get("id", "")
    if configured_id and selected_id != configured_id:
        return (
            False,
            "YNAB_BUDGET_ID is set, but it did not match any returned YNAB plan.",
        )

    name = plan_label(selected_plan)
    snapshot_result = load_snapshot(YnabClient(config["token"]), selected_id, name)
    snapshot = snapshot_result.snapshot

    lines = [
        "Njord spending review",
        f"Plan: {name}",
    ]

    if not snapshot_result.ok or snapshot is None:
        lines.extend(
            [
                "",
                "Connection status: connected to YNAB plan list.",
                f"Snapshot status: {snapshot_result.message}",
                "I can see the selected plan, but could not load transactions for review.",
            ]
        )
        return False, "\n".join(lines)

    try:
        review = review_spending(snapshot, period=period, start=start, end=end)
    except ValueError as exc:
        return False, str(exc)

    lines.extend(
        [
            f"Period: {review.period.label} ({review.period.start} to {review.period.end})",
            f"Snapshot freshness: {snapshot.metadata.fetched_at}",
            "",
            "Totals",
            f"- Income: {format_currency(review.totals.income)}",
            f"- Outflows: {format_currency(review.totals.outflows)}",
            f"- Net cash flow: {format_currency(review.totals.net_cash_flow)}",
            f"- Transactions reviewed: {review.totals.transaction_count}",
        ]
    )

    if review.comparison is not None:
        comparison = review.comparison
        lines.extend(
            [
                "",
                "Previous period comparison",
                (
                    f"- Compared with {comparison.previous_range.start} to "
                    f"{comparison.previous_range.end}"
                ),
                f"- Income change: {format_currency(comparison.income_delta)}",
                f"- Outflow change: {format_currency(comparison.outflow_delta)}",
                f"- Net cash flow change: {format_currency(comparison.net_cash_flow_delta)}",
            ]
        )

    if review.top_categories:
        lines.append("")
        lines.append("Top spending categories")
        for category in review.top_categories:
            lines.append(
                f"- {category.category_name}: {format_currency(category.outflow)} "
                f"across {category.transaction_count} transaction(s)"
            )

    if review.notable_transactions:
        lines.append("")
        lines.append("Notable transactions")
        for transaction in review.notable_transactions:
            lines.append(
                f"- {transaction.date} {transaction.payee_name}: "
                f"{format_currency(transaction.amount)} "
                f"({transaction.category_name}, {transaction.reason})"
            )

    lines.extend(
        [
            "",
            "Observations",
            "- This review is factual and does not recommend budget changes by itself.",
        ]
    )
    return True, "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Review YNAB spending for a month or explicit date range."
    )
    parser.add_argument(
        "--period",
        choices=("current-month", "previous-month"),
        default="current-month",
        help="Named period to review when --from and --to are not provided.",
    )
    parser.add_argument(
        "--from",
        dest="start_date",
        help="Start date for a custom review range, in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--to",
        dest="end_date",
        help="End date for a custom review range, in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "request",
        nargs=argparse.REMAINDER,
        help=argparse.SUPPRESS,
    )
    return parser


def main() -> None:
    configure_output()
    parser = build_parser()
    args = parser.parse_args()
    try:
        start = parse_cli_date(args.start_date, "--from")
        end = parse_cli_date(args.end_date, "--to")
    except ValueError as exc:
        parser.error(str(exc))

    ok, output = load_spending_review(args.period, start=start, end=end)
    print(output)
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
