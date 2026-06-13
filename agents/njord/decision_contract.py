"""LLM decision contract validation for Njord finance loops."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fact_packet import FinanceFactPacket


REQUIRED_FIELDS = {
    "recommendation",
    "rationale",
    "confidence",
    "assumptions",
    "risks",
    "requires_user_approval",
}

FORBIDDEN_WRITE_TERMS = (
    "changed ynab",
    "updated ynab",
    "moved money",
    "execute the write",
    "executed the write",
    "approved cash floor violation",
    "override cash floor",
    "ignore cash floor",
    "mutate state",
    "write to ynab",
)


@dataclass(frozen=True)
class DecisionValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        if self.ok:
            if self.warnings:
                return "LLM decision contract valid with warnings: " + "; ".join(self.warnings)
            return "LLM decision contract valid."
        return "LLM decision contract invalid: " + "; ".join(self.errors)


def validate_llm_decision(
    payload: dict[str, Any],
    fact_packet: FinanceFactPacket,
) -> DecisionValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    missing = sorted(REQUIRED_FIELDS - set(payload.keys()))
    if missing:
        errors.append("missing required field(s): " + ", ".join(missing))

    recommendation = str(payload.get("recommendation", "")).strip()
    rationale = str(payload.get("rationale", "")).strip()
    assumptions = payload.get("assumptions")
    risks = payload.get("risks")
    confidence = payload.get("confidence")
    requires_approval = payload.get("requires_user_approval")

    if "recommendation" in payload and not recommendation:
        errors.append("recommendation must not be empty")
    if "rationale" in payload and not rationale:
        errors.append("rationale must not be empty")
    if "assumptions" in payload and not isinstance(assumptions, list):
        errors.append("assumptions must be a list")
    if "risks" in payload and not isinstance(risks, list):
        errors.append("risks must be a list")
    if "requires_user_approval" in payload and not isinstance(requires_approval, bool):
        errors.append("requires_user_approval must be a boolean")

    if "confidence" in payload:
        if not isinstance(confidence, (int, float)):
            errors.append("confidence must be numeric from 0.0 to 1.0")
        elif confidence < 0 or confidence > 1:
            errors.append("confidence must be between 0.0 and 1.0")

    combined_text = " ".join(
        [
            recommendation,
            rationale,
            " ".join(str(item) for item in assumptions or [] if isinstance(assumptions, list)),
            " ".join(str(item) for item in risks or [] if isinstance(risks, list)),
        ]
    ).lower()
    for term in FORBIDDEN_WRITE_TERMS:
        if term in combined_text:
            errors.append(f"forbidden write or override claim: {term}")

    if "balance" in combined_text and any(
        verb in combined_text for verb in ("set ", "change ", "alter ", "adjust ")
    ):
        errors.append("LLM output appears to alter balances")

    fact_text = fact_packet.to_prompt_context().lower()
    suspicious_numbers = [
        token
        for token in combined_text.replace("$", " ").replace(",", " ").split()
        if token.replace(".", "", 1).isdigit() and token not in fact_text
    ]
    if suspicious_numbers:
        warnings.append("LLM output contains numeric values not found in the fact packet")

    if fact_packet.generated_facts.get("cash_floor_breach_date") and requires_approval is False:
        errors.append("cash floor breach recommendations must require user approval")

    return DecisionValidationResult(ok=not errors, errors=errors, warnings=warnings)

