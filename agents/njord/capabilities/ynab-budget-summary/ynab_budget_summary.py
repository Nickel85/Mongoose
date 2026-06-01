"""Read-only YNAB budget summary capability for Njord."""

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
from review import review_snapshot
from snapshot import load_snapshot
from ynab_api import YnabClient, choose_plan, format_currency, list_plans


def configure_output() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def plan_label(plan: dict[str, Any]) -> str:
    return plan.get("name") or plan.get("id") or "selected YNAB plan"


def load_latest_summary() -> tuple[bool, str]:
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
        "Njord budget summary",
        f"Date: {date.today().isoformat()}",
        f"Plan: {name}",
        f"Plans available: {len(plans)}",
    ]

    if not snapshot_result.ok or snapshot is None:
        lines.extend(
            [
                "",
                "Connection status: connected to YNAB plan list.",
                f"Snapshot status: {snapshot_result.message}",
                "I can see the selected plan, but could not load the normalized snapshot yet.",
            ]
        )
        return False, "\n".join(lines)

    on_budget_accounts = snapshot.open_on_budget_accounts()
    categories_with_balance = snapshot.categories_with_balance()
    review = review_snapshot(snapshot)

    lines.extend(
        [
            "",
            "Snapshot",
            f"- Open on-budget accounts: {len(on_budget_accounts)}",
            f"- On-budget account balance: {format_currency(snapshot.total_on_budget_balance())}",
            f"- Categories with assigned balances: {len(categories_with_balance)}",
            f"- Review-needed flags: {len(review.flags)}",
            f"- Months loaded: {len(snapshot.months)}",
            f"- Transactions loaded: {len(snapshot.transactions)}",
            f"- Scheduled transactions loaded: {len(snapshot.scheduled_transactions)}",
            f"- Snapshot freshness: {snapshot.metadata.fetched_at}",
        ]
    )

    if review.flags:
        lines.append("")
        lines.append("Review needed")
        for flag in review.flags[:7]:
            amount = f" ({format_currency(flag.amount)})" if flag.amount is not None else ""
            lines.append(
                f"- [{flag.severity}/{flag.confidence}] {flag.subject_name}{amount}: "
                f"{flag.detail}"
            )

    lines.extend(
        [
            "",
            "Next step",
            "- Review flagged items first; they are attention prompts, not automatic recommendations.",
        ]
    )

    return True, "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Summarize the latest available YNAB budget state."
    )
    return parser


def main() -> None:
    configure_output()
    build_parser().parse_args()
    ok, output = load_latest_summary()
    print(output)
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()

