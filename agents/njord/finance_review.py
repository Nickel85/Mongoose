"""Interaction-first Njord finance review capability."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from config import ConfigFileError, current_config_snapshot
from decision_contract import validate_llm_decision
from fact_packet import (
    FinanceFactPacket,
    build_cash_flow_fact_packet,
    build_financial_risk_fact_packet,
)
from loop_contract import get_contract
from review import review_snapshot
from snapshot import FinancialSnapshot, load_snapshot
from spending import review_spending
from ynab_api import YnabClient, choose_plan, format_currency, list_plans


@dataclass(frozen=True)
class FinanceReviewResult:
    ok: bool
    output: str
    fact_packets: list[FinanceFactPacket]


def build_finance_review_from_snapshot(snapshot: FinancialSnapshot) -> FinanceReviewResult:
    spending = review_spending(snapshot)
    review_summary = review_snapshot(snapshot)
    review_flags = [flag.to_dict() for flag in review_summary.flags]
    cash_flow = build_cash_flow_fact_packet(snapshot, spending)
    risk = build_financial_risk_fact_packet(
        snapshot,
        spending,
        review_flags,
        cash_flow_packet=cash_flow,
    )
    validation = validate_llm_decision(
        {
            "recommendation": "Review the deterministic finance facts before requesting a budget change.",
            "rationale": "The v0.8 finance review is read-only and uses validated fact packets.",
            "confidence": 0.8,
            "assumptions": [
                "The loaded YNAB snapshot is the current source of truth.",
                "Missing scheduled transaction data lowers forecast confidence.",
            ],
            "risks": [
                "Short review periods can make cash flow look worse than the full month.",
                "No budget changes are executed from this review.",
            ],
            "requires_user_approval": True,
        },
        risk,
    )
    lines = [
        "Njord finance review",
        f"Plan: {snapshot.metadata.plan_name}",
        f"Snapshot: {snapshot.metadata.fetched_at}",
        "",
        "Loop contract",
        f"- {get_contract('cash-flow-forecasting').name}: calculate_only; LLM role: none.",
        f"- {get_contract('financial-risk').name}: score_and_explain; LLM role: explain only.",
        "",
        "Cash Flow Forecasting",
        f"- Current cash: {cash_flow.generated_facts['current_cash_display']}",
        f"- Income: {cash_flow.generated_facts['income_display']}",
        f"- Outflows: {cash_flow.generated_facts['outflows_display']}",
        f"- Net cash flow: {cash_flow.generated_facts['net_cash_flow_display']}",
        (
            "- Estimated daily net cash flow: "
            f"{cash_flow.generated_facts['estimated_daily_net_cash_flow_display']}"
        ),
        f"- Cash floor breach date: {cash_flow.generated_facts['cash_floor_breach_date'] or 'not detected'}",
        f"- Forecast confidence: {cash_flow.confidence}",
        "",
        "Financial Risk",
        f"- Risk score: {risk.generated_facts['risk_score']} ({risk.generated_facts['risk_band']})",
        f"- High-severity flags: {risk.generated_facts['high_flag_count']}",
        f"- Medium-severity flags: {risk.generated_facts['medium_flag_count']}",
        "- Top risks:",
    ]
    lines.extend(f"  - {item}" for item in risk.generated_facts["top_risks"])
    lines.extend(
        [
            "- Mitigation actions:",
            *[f"  - {item}" for item in risk.generated_facts["mitigation_actions"]],
            "",
            "Fact packets",
            f"- {cash_flow.packet_id}: {cash_flow.capability}; confidence {cash_flow.confidence}",
            f"- {risk.packet_id}: {risk.capability}; confidence {risk.confidence}",
            "",
            "LLM decision validation",
            f"- {validation.summary()}",
            "",
            "Guardrails",
            "- This review is read-only.",
            "- Natural-language requests cannot mutate YNAB before guarded write execution exists.",
            "- LLM output may explain or rank validated facts, but cannot calculate balances or approve writes.",
            "",
            "Next actions",
            "- Ask Njord follow-up questions in the REPL.",
            "- Use future guarded planning only after reviewing these facts.",
        ]
    )
    if cash_flow.missing_data or risk.missing_data:
        missing = sorted(set(cash_flow.missing_data + risk.missing_data))
        lines.extend(["", "Missing or weak data"])
        lines.extend(f"- {item}" for item in missing)

    return FinanceReviewResult(True, "\n".join(lines), [cash_flow, risk])


def load_finance_review() -> tuple[bool, str]:
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

    if not config["token"]:
        return (
            False,
            "YNAB_ACCESS_TOKEN is not configured. Run 'Njord config status' for setup details.",
        )
    if not config["budget_id"]:
        return (
            False,
            "YNAB_BUDGET_ID is not configured. Run 'Njord config status' to validate available plans.",
        )

    plans_result = list_plans()
    if not plans_result.ok:
        return False, plans_result.message
    selected_plan = choose_plan(plans_result.items, config["budget_id"])
    if selected_plan is None:
        return False, "No YNAB plan could be selected."
    selected_id = selected_plan.get("id", "")
    name = selected_plan.get("name") or selected_id or "selected YNAB plan"

    snapshot_result = load_snapshot(YnabClient(config["token"]), selected_id, name)
    if not snapshot_result.ok or snapshot_result.snapshot is None:
        return (
            False,
            "\n".join(
                [
                    "Njord finance review",
                    f"Plan: {name}",
                    "",
                    "Connection status: connected to YNAB plan list.",
                    f"Snapshot status: {snapshot_result.message}",
                    "The finance review needs a full read-only snapshot before it can build fact packets.",
                ]
            ),
        )
    result = build_finance_review_from_snapshot(snapshot_result.snapshot)
    return result.ok, result.output


def summarize_fact_packet(packet: FinanceFactPacket) -> dict[str, Any]:
    return {
        "packet_id": packet.packet_id,
        "capability": packet.capability,
        "confidence": packet.confidence,
        "source_snapshot_ids": packet.source_snapshot_ids,
        "generated_facts": packet.generated_facts,
    }

