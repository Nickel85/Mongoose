"""Natural-language request routing for Midas."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Route:
    capability: str
    reason: str


def route_request(request: str) -> Route:
    normalized = request.lower()

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
    )
    greeting_terms = ("hello", "hi", "hey", "test", "connection")

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
        reason="Defaulting to the financial summary capability for Midas.",
    )

