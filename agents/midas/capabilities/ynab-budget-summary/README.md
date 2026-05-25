# YNAB Budget Summary

## Purpose

Use the YNAB API to collect budget data and produce an accountant-style summary of personal finances.

This capability should answer: what happened, where the money is, where it went, and what needs attention.

## When To Use

Use this capability when the user asks to:

- Summarize a YNAB budget.
- Review spending for a month or date range.
- Compare current financials to a prior period.
- Inspect category balances or overspending.
- Prepare a weekly or monthly financial brief.
- Identify transactions, categories, accounts, or trends that need review.

## Inputs

- YNAB API token or OAuth access token loaded from `YNAB_ACCESS_TOKEN`.
- Budget or plan identifier loaded from `YNAB_BUDGET_ID`, or permission to use the default budget.
- Date range, if the user wants a specific period.
- Optional focus area, such as income, spending, debt, savings, category groups, or cash flow.

## Outputs

The output should include:

- Executive summary.
- Account balance snapshot.
- Income and spending summary.
- Category activity summary.
- Overspending or underfunded category notes.
- Notable transactions or unusual changes.
- Questions or follow-up data needed.
- Recommendations only when supported by the data.

The current starter implementation returns a latest budget snapshot with the selected YNAB plan, open on-budget accounts, total on-budget account balance, category counts, and any negative category balances that need review.

## Usage

From the repository root, let the agent route a natural-language request:

```powershell
python agents\midas\agent.py ask "Hey Midas, get me my latest budget."
```

Or call the capability directly:

```powershell
python agents\midas\agent.py ynab-budget-summary
```

The command reads `YNAB_ACCESS_TOKEN` and `YNAB_BUDGET_ID` from the repository root `.env` file.

Example prompts that route here:

```powershell
python agents\midas\agent.py ask "Hey Midas, get me my latest budget."
python agents\midas\agent.py ask "What categories need my attention?"
python agents\midas\agent.py ask "Summarize my current financial picture."
```

## Workflow

1. Authenticate to the YNAB API using a bearer token.
2. Resolve the target budget or plan.
3. Retrieve relevant accounts, categories, months, and transactions.
4. Normalize YNAB milliunit amounts into currency values.
5. Calculate period totals, category totals, account balances, and notable deltas.
6. Separate factual findings from interpretation.
7. Present a concise summary with clear next actions.

## API Notes

Use the official YNAB API documentation as the source of truth: [https://api.ynab.com/](https://api.ynab.com/)

The API uses bearer-token authentication. The current documentation also notes that API endpoints use `plans/{plan_id}` as the primary resource path, while budget-oriented examples and older clients may still refer to `budgets/{budget_id}`. Confirm the endpoint shape during implementation instead of hard-coding stale assumptions.

Common data needed by this capability includes:

- Budgets or plans.
- Accounts.
- Categories and category groups.
- Months.
- Transactions.
- Scheduled transactions, when forecasting future obligations.

## Constraints

- Start read-only.
- Never expose API tokens in logs, summaries, commits, or examples.
- Load secrets from environment variables or a local ignored `.env` file.
- Do not modify YNAB data without a separate write capability and explicit user approval.
- Treat financial recommendations as guidance, not professional financial advice.
- Be explicit when data is missing, stale, excluded, or outside the requested date range.
- Avoid judging personal spending; describe patterns and tradeoffs neutrally.

## Examples

User: "Summarize my budget this month."

Expected response:

- Current account balance snapshot.
- Month-to-date income and spending.
- Top spending categories.
- Categories that need attention.
- A short list of recommended reviews.

User: "What changed since last month?"

Expected response:

- Spending delta by category.
- Income delta.
- Account balance movement.
- New or unusually large transactions.
- Explanation of likely causes, with uncertainty called out.
