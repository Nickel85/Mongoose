"""Natural-language request routing for Njord."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Route:
    capability: str
    reason: str


def route_request(request: str) -> Route:
    normalized = request.lower()

    finance_review_terms = (
        "finance review",
        "financial review",
        "review my finances",
        "review my money",
        "risk score",
        "financial risk",
        "cash flow forecast",
        "cashflow forecast",
    )
    config_terms = (
        "config",
        "configuration",
        "credential",
        "credentials",
        "setup",
    )
    brief_terms = (
        "brief",
        "briefing",
        "weekly",
        "cfo-style",
        "cfo style",
        "financial brief",
    )
    budget_terms = (
        "budget",
        "financial",
        "finances",
        "money",
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
    spending_terms = (
        "spending",
        "spend",
        "spent",
        "transaction",
        "transactions",
        "cash flow",
        "cashflow",
        "outflow",
        "outflows",
        "income",
        "current month",
        "this month",
        "previous month",
        "last month",
        "month-to-date",
    )
    greeting_terms = ("hello", "hi", "hey", "test", "connection")

    if any(term in normalized for term in config_terms) and "status" in normalized:
        return Route(
            capability="config-status",
            reason="The request asks for local YNAB configuration status.",
        )

    if any(term in normalized for term in finance_review_terms):
        return Route(
            capability="finance-review",
            reason="The request asks for the interaction-first finance review loop.",
        )

    if any(term in normalized for term in brief_terms):
        return Route(
            capability="brief",
            reason="The request asks for a financial brief.",
        )

    if any(term in normalized for term in spending_terms):
        return Route(
            capability="ynab-spending-review",
            reason="The request asks about spending, transactions, or cash flow.",
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


