"""Manual financial brief capability for Njord."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


AGENT_ROOT = Path(__file__).resolve().parents[2]
if str(AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_ROOT))

from brief import build_brief, render_brief
from config import ConfigFileError, current_config_snapshot
from snapshot import load_snapshot
from ynab_api import YnabClient, choose_plan, list_plans


def configure_output() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def plan_label(plan: dict[str, Any]) -> str:
    return plan.get("name") or plan.get("id") or "selected YNAB plan"


def load_manual_brief() -> tuple[bool, str]:
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

    snapshot_result = load_snapshot(
        YnabClient(config["token"]),
        selected_id,
        plan_label(selected_plan),
    )
    if not snapshot_result.ok or snapshot_result.snapshot is None:
        return (
            False,
            "\n".join(
                [
                    "Njord weekly financial brief",
                    f"Plan: {plan_label(selected_plan)}",
                    "",
                    "Connection status: connected to YNAB plan list.",
                    f"Snapshot status: {snapshot_result.message}",
                    "I can see the selected plan, but could not load enough data for the brief.",
                ]
            ),
        )

    return True, render_brief(build_brief(snapshot_result.snapshot))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Produce a manual weekly-style Njord financial brief."
    )
    parser.add_argument(
        "request",
        nargs=argparse.REMAINDER,
        help=argparse.SUPPRESS,
    )
    return parser


def main() -> None:
    configure_output()
    build_parser().parse_args()
    ok, output = load_manual_brief()
    print(output)
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
