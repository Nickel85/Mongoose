"""Read-only YNAB budget summary capability for Personal CFO."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import Any


AGENT_ROOT = Path(__file__).resolve().parents[2]
if str(AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_ROOT))

from config import ynab_budget_id
from ynab_api import get_json


def configure_output() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def milliunits_to_currency(amount: int | float | None) -> float:
    return (amount or 0) / 1000


def currency(amount: int | float | None) -> str:
    return f"${milliunits_to_currency(amount):,.2f}"


def choose_plan(plans: list[dict[str, Any]], configured_id: str) -> dict[str, Any] | None:
    if configured_id:
        for plan in plans:
            if plan.get("id") == configured_id:
                return plan

    if len(plans) == 1:
        return plans[0]

    return plans[0] if plans else None


def plan_label(plan: dict[str, Any]) -> str:
    return plan.get("name") or plan.get("id") or "selected YNAB plan"


def load_latest_summary() -> tuple[bool, str]:
    plans_result = get_json("plans")
    if not plans_result.ok:
        return False, plans_result.message

    plans = plans_result.data.get("data", {}).get("plans", [])
    if not plans:
        return False, "YNAB connection succeeded, but no plans were returned."

    configured_id = ynab_budget_id()
    selected_plan = choose_plan(plans, configured_id)
    if selected_plan is None:
        return False, "No YNAB plan could be selected."

    selected_id = selected_plan.get("id", "")
    if configured_id and selected_id != configured_id:
        return (
            False,
            "YNAB_BUDGET_ID is set, but it did not match any returned YNAB plan.",
        )

    plan_result = get_json(f"plans/{selected_id}")
    plan_data = plan_result.data.get("data", {}).get("plan", {}) if plan_result.ok else {}

    name = plan_label(plan_data or selected_plan)
    accounts = plan_data.get("accounts", [])
    categories = plan_data.get("categories", [])

    on_budget_accounts = [
        account
        for account in accounts
        if not account.get("closed") and account.get("on_budget", True)
    ]
    total_balance = sum(account.get("balance", 0) for account in on_budget_accounts)
    categories_with_balance = [
        category
        for category in categories
        if not category.get("hidden") and category.get("balance", 0) != 0
    ]
    underfunded_categories = [
        category
        for category in categories
        if not category.get("hidden") and category.get("balance", 0) < 0
    ]

    lines = [
        "Personal CFO budget summary",
        f"Date: {date.today().isoformat()}",
        f"Plan: {name}",
        f"Plans available: {len(plans)}",
    ]

    if not plan_result.ok:
        lines.extend(
            [
                "",
                "Connection status: connected to YNAB plan list.",
                f"Detail status: {plan_result.message}",
                "I can see the selected plan, but could not load plan details yet.",
            ]
        )
        return False, "\n".join(lines)

    lines.extend(
        [
            "",
            "Snapshot",
            f"- Open on-budget accounts: {len(on_budget_accounts)}",
            f"- On-budget account balance: {currency(total_balance)}",
            f"- Categories with assigned balances: {len(categories_with_balance)}",
            f"- Categories needing review: {len(underfunded_categories)}",
        ]
    )

    if underfunded_categories:
        lines.append("")
        lines.append("Categories needing review")
        for category in underfunded_categories[:5]:
            lines.append(f"- {category.get('name', 'Unnamed category')}: {currency(category.get('balance'))}")

    lines.extend(
        [
            "",
            "Next step",
            "- Ask for a monthly spending review once the transactions summary capability is built.",
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
