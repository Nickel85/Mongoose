"""Deterministic fact packets for Njord AI capability loops."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from snapshot import FinancialSnapshot
from spending import SpendingReview
from ynab_api import format_currency


@dataclass(frozen=True)
class FinanceFactPacket:
    packet_id: str
    capability: str
    source_snapshot_ids: list[str]
    generated_facts: dict[str, Any]
    constraints: list[str]
    protected_rules: list[str]
    candidate_options: list[dict[str, Any]]
    confidence: str
    provenance: list[dict[str, str]]
    missing_data: list[str] = field(default_factory=list)
    stale_data: list[str] = field(default_factory=list)
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_prompt_context(self) -> str:
        prompt_safe = {
            "packet_id": self.packet_id,
            "capability": self.capability,
            "source_snapshot_ids": self.source_snapshot_ids,
            "generated_facts": self.generated_facts,
            "constraints": self.constraints,
            "protected_rules": self.protected_rules,
            "candidate_options": self.candidate_options,
            "confidence": self.confidence,
            "provenance": self.provenance,
            "missing_data": self.missing_data,
            "stale_data": self.stale_data,
        }
        return json.dumps(prompt_safe, indent=2, sort_keys=True)


def snapshot_id(snapshot: FinancialSnapshot) -> str:
    source = {
        "source": snapshot.metadata.source,
        "plan_id": snapshot.metadata.plan_id,
        "fetched_at": snapshot.metadata.fetched_at,
        "includes": snapshot.metadata.includes,
    }
    digest = hashlib.sha256(json.dumps(source, sort_keys=True).encode("utf-8")).hexdigest()
    return f"ynab:{snapshot.metadata.plan_id}:{digest[:12]}"


def packet_id(capability: str, snapshot: FinancialSnapshot, facts: dict[str, Any]) -> str:
    source = {
        "capability": capability,
        "snapshot_id": snapshot_id(snapshot),
        "facts": facts,
    }
    digest = hashlib.sha256(json.dumps(source, sort_keys=True).encode("utf-8")).hexdigest()
    return f"{capability}:{digest[:12]}"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def build_cash_flow_fact_packet(
    snapshot: FinancialSnapshot,
    spending: SpendingReview,
    *,
    cash_floor: int = 0,
) -> FinanceFactPacket:
    period_days = max((spending.period.end - spending.period.start).days + 1, 1)
    daily_net = int(spending.totals.net_cash_flow / period_days)
    current_cash = snapshot.total_on_budget_balance()
    days_until_floor: int | None = None
    breach_date: str | None = None
    if daily_net < 0 and current_cash > cash_floor:
        days_until_floor = max(int((current_cash - cash_floor) / abs(daily_net)), 0)
        breach_date = str(spending.period.end)
    confidence = "medium"
    missing_data: list[str] = []
    stale_data: list[str] = []
    if not snapshot.scheduled_transactions:
        missing_data.append("scheduled_transactions")
        confidence = "low"
    if spending.totals.transaction_count == 0:
        missing_data.append("period_transactions")
        confidence = "low"

    facts = {
        "period": spending.period.to_dict(),
        "current_cash": current_cash,
        "current_cash_display": format_currency(current_cash),
        "income": spending.totals.income,
        "income_display": format_currency(spending.totals.income),
        "outflows": spending.totals.outflows,
        "outflows_display": format_currency(spending.totals.outflows),
        "net_cash_flow": spending.totals.net_cash_flow,
        "net_cash_flow_display": format_currency(spending.totals.net_cash_flow),
        "estimated_daily_net_cash_flow": daily_net,
        "estimated_daily_net_cash_flow_display": format_currency(daily_net),
        "cash_floor": cash_floor,
        "cash_floor_display": format_currency(cash_floor),
        "cash_floor_breach_date": breach_date,
        "days_until_cash_floor": days_until_floor,
        "transaction_count": spending.totals.transaction_count,
    }
    return FinanceFactPacket(
        packet_id=packet_id("cash-flow-forecasting", snapshot, facts),
        capability="cash-flow-forecasting",
        source_snapshot_ids=[snapshot_id(snapshot)],
        generated_facts=facts,
        constraints=[
            "Read-only forecast; no budget state changes are permitted.",
            "Cash floor breach must be warning-only until guarded planning exists.",
        ],
        protected_rules=[
            "Do not invent income, bills, balances, or transactions.",
            "Do not approve spending that violates the cash floor.",
        ],
        candidate_options=[
            {
                "id": "review-cash-flow",
                "description": "Review whether negative cash flow is expected timing or budget pressure.",
            }
        ],
        confidence=confidence,
        provenance=[
            {"field": "current_cash", "source": "snapshot.open_on_budget_accounts"},
            {"field": "period totals", "source": "spending.review_spending"},
        ],
        missing_data=missing_data,
        stale_data=stale_data,
        created_at=utc_now(),
    )


def build_financial_risk_fact_packet(
    snapshot: FinancialSnapshot,
    spending: SpendingReview,
    review_flags: list[dict[str, Any]],
    *,
    cash_flow_packet: FinanceFactPacket,
) -> FinanceFactPacket:
    high_flags = [flag for flag in review_flags if flag.get("severity") == "high"]
    medium_flags = [flag for flag in review_flags if flag.get("severity") == "medium"]
    negative_categories = [
        flag for flag in review_flags if flag.get("rule_id") == "negative-category-balance"
    ]
    risk_score = 20
    risk_score += min(len(high_flags) * 15, 45)
    risk_score += min(len(medium_flags) * 7, 21)
    if spending.totals.net_cash_flow < 0:
        risk_score += 15
    if cash_flow_packet.generated_facts.get("cash_floor_breach_date"):
        risk_score += 20
    risk_score = min(risk_score, 100)
    confidence = "medium"
    missing_data: list[str] = []
    if cash_flow_packet.missing_data:
        missing_data.extend(cash_flow_packet.missing_data)
        confidence = "low"

    top_risks = []
    if spending.totals.net_cash_flow < 0:
        top_risks.append(
            f"Net cash flow is {format_currency(spending.totals.net_cash_flow)} for the review period."
        )
    top_risks.extend(
        f"{flag.get('title')}: {flag.get('subject_name')}" for flag in high_flags[:3]
    )
    if not top_risks:
        top_risks.append("No high-severity deterministic risk drivers were detected.")

    facts = {
        "risk_score": risk_score,
        "risk_band": risk_band(risk_score),
        "high_flag_count": len(high_flags),
        "medium_flag_count": len(medium_flags),
        "negative_category_count": len(negative_categories),
        "top_risks": top_risks,
        "mitigation_actions": [
            "Review high-severity flags before budget-changing decisions.",
            "Confirm cash-flow timing before moving money.",
            "Keep all YNAB changes behind future explicit approval.",
        ],
        "cash_flow_packet_id": cash_flow_packet.packet_id,
    }
    return FinanceFactPacket(
        packet_id=packet_id("financial-risk", snapshot, facts),
        capability="financial-risk",
        source_snapshot_ids=[snapshot_id(snapshot)],
        generated_facts=facts,
        constraints=[
            "Risk score is deterministic and cannot be changed by an LLM.",
            "Risk explanation is recommendation-only and cannot mutate YNAB.",
        ],
        protected_rules=[
            "Do not override protected cash floor rules.",
            "Do not convert risk explanation into write execution.",
        ],
        candidate_options=[
            {
                "id": "review-top-risks",
                "description": "Review the highest risk drivers before requesting a budget plan.",
            }
        ],
        confidence=confidence,
        provenance=[
            {"field": "risk_score", "source": "deterministic risk scoring"},
            {"field": "review_flags", "source": "review.review_snapshot"},
            {"field": "cash_flow", "source": cash_flow_packet.packet_id},
        ],
        missing_data=missing_data,
        created_at=utc_now(),
    )


def risk_band(score: int) -> str:
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"

