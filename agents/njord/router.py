"""Natural-language request routing for Njord."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Route:
    capability: str
    reason: str


def route_request(request: str) -> Route:
    normalized = request.lower()

    config_terms = (
        "config",
        "configuration",
        "credential",
        "credentials",
        "setup",
    )
    budget_terms = (
        "budget",
        "financial",
        "finances",
        "money",
        "spending",
        "ynab",
        "latest",
        "summary",
        "cash",
        "account",
        "attention",
        "review",
        "flag",
        "flags",
    )
    greeting_terms = ("hello", "hi", "hey", "test", "connection")

    if any(term in normalized for term in config_terms) and "status" in normalized:
        return Route(
            capability="config-status",
            reason="The request asks for local YNAB configuration status.",
        )

    if any(term in normalized for term in budget_terms):
        return Route(
            capability="ynab-budget-summary",
            reason="The request asks about budget or financial information.",
        )

    if any(term in normalized for term in greeting_terms):
        return Route(
            capability="hello-world",
            reason="The request looks like a greeting or connection test.",
        )

    return Route(
        capability="ynab-budget-summary",
        reason="Defaulting to the financial summary capability for Njord.",
    )


