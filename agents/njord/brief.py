"""Manual financial brief composition for Njord."""

from __future__ import annotations

from dataclasses import dataclass

from recommendations import RecommendationSummary, generate_recommendations
from review import ReviewSummary, review_snapshot
from snapshot import FinancialSnapshot
from spending import SpendingReview, review_spending
from ynab_api import format_currency


@dataclass(frozen=True)
class Brief:
    snapshot: FinancialSnapshot
    review: ReviewSummary
    spending: SpendingReview
    recommendations: RecommendationSummary

    def to_dict(self) -> dict[str, object]:
        return {
            "snapshot": self.snapshot.to_dict(),
            "review": self.review.to_dict(),
            "spending": self.spending.to_dict(),
            "recommendations": self.recommendations.to_dict(),
        }


def build_brief(snapshot: FinancialSnapshot) -> Brief:
    review = review_snapshot(snapshot)
    spending = review_spending(snapshot)
    recommendations = generate_recommendations(review, spending)
    return Brief(
        snapshot=snapshot,
        review=review,
        spending=spending,
        recommendations=recommendations,
    )


def render_brief(brief: Brief) -> str:
    snapshot = brief.snapshot
    spending = brief.spending
    review = brief.review
    recommendations = brief.recommendations
    on_budget_accounts = snapshot.open_on_budget_accounts()

    lines = [
        "Njord weekly financial brief",
        f"Plan: {snapshot.metadata.plan_name}",
        f"Snapshot freshness: {snapshot.metadata.fetched_at}",
        "",
        "Observations",
        f"- Open on-budget accounts: {len(on_budget_accounts)}",
        f"- On-budget account balance: {format_currency(snapshot.total_on_budget_balance())}",
        (
            f"- Current month cash flow: {format_currency(spending.totals.net_cash_flow)} "
            f"({format_currency(spending.totals.income)} income, "
            f"{format_currency(spending.totals.outflows)} outflows)"
        ),
        f"- Transactions reviewed: {spending.totals.transaction_count}",
        f"- Review-needed flags: {len(review.flags)}",
        f"- Recommended next actions: {len(recommendations.recommendations)}",
    ]

    if spending.comparison is not None:
        lines.extend(
            [
                (
                    f"- Compared with {spending.comparison.previous_range.start} to "
                    f"{spending.comparison.previous_range.end}: "
                    f"{format_currency(spending.comparison.net_cash_flow_delta)} "
                    "net cash-flow change"
                )
            ]
        )

    if spending.top_categories:
        lines.append("")
        lines.append("Spending highlights")
        for category in spending.top_categories[:5]:
            lines.append(
                f"- {category.category_name}: {format_currency(category.outflow)} "
                f"across {category.transaction_count} transaction(s)"
            )

    if spending.notable_transactions:
        lines.append("")
        lines.append("Notable transactions")
        for transaction in spending.notable_transactions[:5]:
            lines.append(
                f"- {transaction.date} {transaction.payee_name}: "
                f"{format_currency(transaction.amount)} "
                f"({transaction.category_name}, {transaction.reason})"
            )

    lines.append("")
    lines.append("Review items")
    if review.flags:
        for flag in review.flags[:7]:
            amount = f" ({format_currency(flag.amount)})" if flag.amount is not None else ""
            lines.append(
                f"- [{flag.severity}/{flag.confidence}] {flag.subject_name}{amount}: "
                f"{flag.detail}"
            )
    else:
        lines.append("- No deterministic review-needed flags were found in the loaded snapshot.")

    lines.append("")
    lines.append("Suggested next actions")
    if recommendations.recommendations:
        for recommendation in recommendations.recommendations[:5]:
            lines.append(
                f"- [{recommendation.confidence}] {recommendation.title}: "
                f"{recommendation.recommendation}"
            )
            lines.append(f"  Expected impact: {recommendation.expected_impact}")
            if recommendation.risks:
                lines.append(f"  Risk/tradeoff: {recommendation.risks[0]}")
    else:
        lines.append("- No recommendation met the deterministic evidence threshold.")

    lines.extend(
        [
            "",
            "Boundaries",
            "- This brief is read-only and does not modify YNAB.",
            "- Suggested actions are review prompts, not automatic financial decisions.",
        ]
    )

    return "\n".join(lines)
