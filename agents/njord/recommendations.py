"""Evidence-backed recommendation generation for Njord."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from review import ReviewFlag, ReviewSummary
from spending import SpendingReview


@dataclass(frozen=True)
class Recommendation:
    id: str
    title: str
    facts: list[str]
    interpretation: str
    recommendation: str
    expected_impact: str
    confidence: str
    risks: list[str]
    evidence: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RecommendationSummary:
    recommendations: list[Recommendation]

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommendations": [
                recommendation.to_dict() for recommendation in self.recommendations
            ]
        }


def generate_recommendations(
    review: ReviewSummary,
    spending: SpendingReview | None = None,
) -> RecommendationSummary:
    recommendations: list[Recommendation] = []
    recommendations.extend(category_balance_recommendations(review))
    recommendations.extend(transaction_review_recommendations(review))
    if spending is not None:
        recommendations.extend(spending_pattern_recommendations(spending))
        recommendations.extend(cash_flow_recommendations(spending))

    return RecommendationSummary(
        recommendations=dedupe_recommendations(recommendations)
    )


def dedupe_recommendations(
    recommendations: list[Recommendation],
) -> list[Recommendation]:
    seen: set[str] = set()
    deduped: list[Recommendation] = []
    for recommendation in recommendations:
        if recommendation.id in seen:
            continue
        seen.add(recommendation.id)
        deduped.append(recommendation)
    return deduped


def flags_by_rule(review: ReviewSummary, rule_id: str) -> list[ReviewFlag]:
    return [flag for flag in review.flags if flag.rule_id == rule_id]


def category_balance_recommendations(
    review: ReviewSummary,
) -> list[Recommendation]:
    negative = flags_by_rule(review, "negative-category-balance")
    underfunded = flags_by_rule(review, "underfunded-category-activity")
    over_budget = flags_by_rule(review, "category-activity-over-budget")
    recommendations: list[Recommendation] = []

    if negative:
        top_flags = sorted(negative, key=lambda flag: abs(flag.amount or 0), reverse=True)[:3]
        recommendations.append(
            Recommendation(
                id="review-negative-category-balances",
                title="Review categories with negative available balances",
                facts=[
                    f"{flag.subject_name} is at {flag.amount} milliunits."
                    for flag in top_flags
                ],
                interpretation=(
                    "Negative available balances usually mean spending exceeded "
                    "the current category allocation."
                ),
                recommendation=(
                    "Review these categories before making new discretionary "
                    "spending decisions or moving money."
                ),
                expected_impact=(
                    "Clarifies which categories may need reallocation or closer "
                    "attention."
                ),
                confidence="high",
                risks=[
                    "A negative balance may be intentional if another category or account offset is planned.",
                    "This recommendation does not modify the budget.",
                ],
                evidence=[flag.to_dict() for flag in top_flags],
            )
        )

    if underfunded:
        top_flags = sorted(underfunded, key=lambda flag: abs(flag.amount or 0), reverse=True)[:3]
        recommendations.append(
            Recommendation(
                id="review-unfunded-spending",
                title="Check spending that has little or no assigned budget coverage",
                facts=[
                    f"{flag.subject_name} has activity of {flag.amount} milliunits."
                    for flag in top_flags
                ],
                interpretation=(
                    "Spending with little or no assigned budget coverage can make "
                    "cash-flow pressure harder to see."
                ),
                recommendation=(
                    "Confirm whether these categories should receive budget "
                    "coverage or whether the spending was expected."
                ),
                expected_impact=(
                    "Improves visibility into categories that may otherwise be "
                    "missed in a weekly brief."
                ),
                confidence="medium",
                risks=[
                    "Some categories may be intentionally left unassigned until later in the month.",
                    "This is a review prompt, not a request to move money.",
                ],
                evidence=[flag.to_dict() for flag in top_flags],
            )
        )

    if over_budget:
        top_flags = sorted(over_budget, key=lambda flag: abs(flag.amount or 0), reverse=True)[:3]
        recommendations.append(
            Recommendation(
                id="review-category-activity-over-budget",
                title="Review categories where activity is above assigned budget",
                facts=[
                    (
                        f"{flag.subject_name} outflow is "
                        f"{flag.evidence.get('activity_outflow', 0)} milliunits "
                        f"against {flag.evidence.get('budgeted', 0)} milliunits budgeted."
                    )
                    for flag in top_flags
                ],
                interpretation=(
                    "Materially higher activity can indicate a one-time expense, "
                    "a timing issue, or a category that needs attention."
                ),
                recommendation=(
                    "Check whether each category reflects expected timing or a "
                    "spending pattern that should be watched."
                ),
                expected_impact=(
                    "Helps separate normal timing differences from categories "
                    "that may need follow-up."
                ),
                confidence="medium",
                risks=[
                    "The current snapshot may not include enough history to identify a true trend.",
                    "One-time purchases can look unusual without additional context.",
                ],
                evidence=[flag.to_dict() for flag in top_flags],
            )
        )

    return recommendations


def transaction_review_recommendations(
    review: ReviewSummary,
) -> list[Recommendation]:
    uncategorized = flags_by_rule(review, "uncategorized-transaction")
    large = flags_by_rule(review, "unusually-large-transaction")
    stale = flags_by_rule(review, "stale-scheduled-transaction")
    recommendations: list[Recommendation] = []

    if uncategorized:
        recommendations.append(
            Recommendation(
                id="categorize-open-transactions",
                title="Categorize transactions missing categories",
                facts=[
                    f"{len(uncategorized)} transaction(s) are uncategorized."
                ],
                interpretation=(
                    "Uncategorized transactions reduce the reliability of spending "
                    "summaries and category-level recommendations."
                ),
                recommendation=(
                    "Categorize these transactions before relying on category "
                    "totals for decisions."
                ),
                expected_impact=(
                    "Makes spending review and future brief output more accurate."
                ),
                confidence="high",
                risks=[
                    "Some imported transactions may still be awaiting normal categorization.",
                    "This recommendation is read-only and does not change transactions.",
                ],
                evidence=[flag.to_dict() for flag in uncategorized[:5]],
            )
        )

    if large:
        top_flags = sorted(large, key=lambda flag: abs(flag.amount or 0), reverse=True)[:3]
        recommendations.append(
            Recommendation(
                id="confirm-large-outflows",
                title="Confirm unusually large outflows",
                facts=[
                    f"{flag.subject_name} is {flag.amount} milliunits."
                    for flag in top_flags
                ],
                interpretation=(
                    "Large outflows can be expected annual bills, but they can also "
                    "distort the current period picture."
                ),
                recommendation=(
                    "Confirm these outflows were expected and categorized correctly."
                ),
                expected_impact=(
                    "Reduces the chance that an unusual transaction is overlooked "
                    "in the weekly review."
                ),
                confidence="medium",
                risks=[
                    "A transaction can be large and still be fully planned.",
                    "Confirming a transaction does not imply it needs correction.",
                ],
                evidence=[flag.to_dict() for flag in top_flags],
            )
        )

    if stale:
        recommendations.append(
            Recommendation(
                id="review-stale-scheduled-transactions",
                title="Review scheduled transactions with stale dates",
                facts=[
                    f"{flag.subject_name} next date is {flag.evidence.get('date_next')}."
                    for flag in stale[:3]
                ],
                interpretation=(
                    "A stale scheduled transaction can make upcoming obligations "
                    "look less reliable."
                ),
                recommendation=(
                    "Check whether these scheduled transactions should be updated, "
                    "skipped, or removed in YNAB."
                ),
                expected_impact=(
                    "Improves confidence in future obligation and brief planning."
                ),
                confidence="medium",
                risks=[
                    "The date may be stale because the loaded snapshot is old.",
                    "This recommendation does not update scheduled transactions.",
                ],
                evidence=[flag.to_dict() for flag in stale[:3]],
            )
        )

    return recommendations


def spending_pattern_recommendations(
    spending: SpendingReview,
) -> list[Recommendation]:
    recommendations: list[Recommendation] = []
    if not spending.top_categories:
        return recommendations

    top = spending.top_categories[0]
    share = top.outflow / spending.totals.outflows if spending.totals.outflows else 0
    if share >= 0.4 and spending.totals.outflows > 0:
        recommendations.append(
            Recommendation(
                id="review-largest-spending-category",
                title="Review the largest spending category for the period",
                facts=[
                    (
                        f"{top.category_name} accounts for {top.outflow} milliunits "
                        f"of {spending.totals.outflows} milliunits in outflows."
                    )
                ],
                interpretation=(
                    "One category represents a large share of period outflows."
                ),
                recommendation=(
                    "Review the category transactions to confirm they match "
                    "expectations for the period."
                ),
                expected_impact=(
                    "Focuses review time on the category most likely to explain "
                    "current spending."
                ),
                confidence="medium",
                risks=[
                    "A high share can be normal for rent, annual bills, or planned purchases.",
                    "This recommendation does not assume the spending is wrong.",
                ],
                evidence=[top.to_dict(), spending.totals.to_dict()],
            )
        )

    return recommendations


def cash_flow_recommendations(
    spending: SpendingReview,
) -> list[Recommendation]:
    if spending.totals.transaction_count == 0:
        return []
    if spending.totals.net_cash_flow >= 0:
        return []

    confidence = "medium" if spending.comparison is not None else "low"
    evidence: list[dict[str, Any]] = [spending.totals.to_dict()]
    if spending.comparison is not None:
        evidence.append(spending.comparison.to_dict())

    return [
        Recommendation(
            id="review-negative-period-cash-flow",
            title="Review negative cash flow for the period",
            facts=[
                f"Net cash flow is {spending.totals.net_cash_flow} milliunits.",
                f"Outflows are {spending.totals.outflows} milliunits.",
                f"Income is {spending.totals.income} milliunits.",
            ],
            interpretation=(
                "Outflows are higher than income in the selected period."
            ),
            recommendation=(
                "Review whether the negative cash flow is expected timing or "
                "something that needs adjustment."
            ),
            expected_impact=(
                "Helps separate planned timing differences from budget pressure."
            ),
            confidence=confidence,
            risks=[
                "Short periods can show negative cash flow even when the full month is healthy.",
                "This recommendation should be weighed against upcoming income and obligations.",
            ],
            evidence=evidence,
        )
    ]
