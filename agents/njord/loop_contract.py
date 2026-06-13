"""AI capability loop contracts for Njord finance workflows."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class CapabilityLoopContract:
    name: str
    mission: str
    trigger: str
    loop_type: str
    llm_role: str
    deterministic_services: list[str]
    inputs: list[str]
    state_read: list[str]
    decision_rules: list[str]
    llm_decision_prompt: str
    outputs: list[str]
    next_actions: list[str]
    escalation_criteria: list[str]
    audit_log: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


LOOP_EXECUTION_ENVELOPE = [
    "detect_trigger",
    "read_state",
    "run_deterministic_services",
    "generate_structured_facts",
    "ask_llm_for_judgment_only",
    "validate_llm_output_against_rules",
    "produce_recommendation",
    "log_decision",
    "update_state_only_after_approval",
]


LLM_DECISION_GUARDRAILS = {
    "allowed_to": [
        "classify ambiguity",
        "rank options",
        "explain tradeoffs",
        "propose recovery actions",
        "summarize system health",
    ],
    "not_allowed_to": [
        "calculate balances",
        "invent transactions",
        "override protected rules",
        "approve cash floor violations",
        "change state without user approval",
    ],
    "required_output": [
        "recommendation",
        "rationale",
        "confidence",
        "assumptions",
        "risks",
        "requires_user_approval",
    ],
}


CONTRACTS: dict[str, CapabilityLoopContract] = {
    "cash-flow-forecasting": CapabilityLoopContract(
        name="Cash Flow Forecasting",
        mission="Predict future cash position from deterministic finance data.",
        trigger="Daily refresh, financial change, or user finance-review request",
        loop_type="calculate_only",
        llm_role="none",
        deterministic_services=[
            "income_projection",
            "bill_schedule",
            "recurring_spend_forecast",
            "period_cash_flow_calculator",
        ],
        inputs=[
            "current_balances",
            "income_schedule",
            "bill_calendar",
            "expected_spending",
            "period_transactions",
        ],
        state_read=[
            "ynab_accounts",
            "ynab_transactions",
            "ynab_scheduled_transactions",
            "ynab_months",
        ],
        decision_rules=[
            "LLM must not calculate balances.",
            "Forecast confidence must reflect missing or stale income and bill data.",
            "No budget state may be changed by this loop.",
        ],
        llm_decision_prompt="No LLM judgment is requested for cash-flow forecasting in v0.8.",
        outputs=[
            "daily_cash_forecast",
            "cash_floor_breach_date",
            "forecast_confidence",
        ],
        next_actions=[
            "review negative cash-flow periods",
            "review stale scheduled transactions",
            "collect missing bill or income assumptions",
        ],
        escalation_criteria=[
            "projected cash falls below the configured cash floor",
            "forecast confidence is low because required source data is missing",
        ],
        audit_log=[
            "trigger",
            "snapshot_id",
            "fact_packet_id",
            "forecast_outputs",
            "validation_result",
        ],
    ),
    "financial-risk": CapabilityLoopContract(
        name="Financial Risk",
        mission="Detect financial fragility and explain the top risk drivers.",
        trigger="Daily review, major financial change, or user finance-review request",
        loop_type="score_and_explain",
        llm_role="Explain top risk drivers and mitigations from validated facts only",
        deterministic_services=[
            "liquidity_ratio_calculator",
            "debt_ratio_calculator",
            "utilization_checker",
            "review_flag_counter",
        ],
        inputs=[
            "income",
            "debts",
            "balances",
            "fixed_expenses",
            "review_flags",
            "cash_flow_forecast",
        ],
        state_read=[
            "ynab_accounts",
            "ynab_categories",
            "ynab_transactions",
            "ynab_scheduled_transactions",
        ],
        decision_rules=[
            "Risk score is calculated deterministically.",
            "LLM may explain risk drivers but cannot change the score.",
            "High risk requires user review before any later planning work.",
        ],
        llm_decision_prompt=(
            "Given the validated risk facts, summarize the top risk drivers, "
            "mitigation actions, assumptions, risks, and whether user approval is required."
        ),
        outputs=[
            "risk_score",
            "top_risks",
            "mitigation_actions",
        ],
        next_actions=[
            "review high-severity risk drivers",
            "collect missing assumptions",
            "defer write planning until risk is understood",
        ],
        escalation_criteria=[
            "risk score is 70 or higher",
            "cash floor breach is detected",
            "negative category balances exist",
        ],
        audit_log=[
            "trigger",
            "snapshot_id",
            "fact_packet_id",
            "risk_score",
            "llm_decision_metadata",
            "validation_result",
        ],
    ),
}


def get_contract(name: str) -> CapabilityLoopContract:
    key = name.strip().lower()
    if key not in CONTRACTS:
        raise KeyError(f"Unknown Njord loop contract: {name}")
    return CONTRACTS[key]


def loop_contract_summary() -> str:
    lines = [
        "Njord AI capability loop contract",
        "",
        "Execution envelope",
    ]
    lines.extend(f"- {step}" for step in LOOP_EXECUTION_ENVELOPE)
    lines.extend(["", "Guardrails"])
    for rule in LLM_DECISION_GUARDRAILS["not_allowed_to"]:
        lines.append(f"- LLM not allowed to {rule}.")
    lines.extend(["", "v0.8 loop contracts"])
    for contract in CONTRACTS.values():
        lines.append(f"- {contract.name}: {contract.loop_type}; LLM role: {contract.llm_role}")
    return "\n".join(lines)

