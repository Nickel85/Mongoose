# YNAB Spending Review

## Purpose

Review YNAB transactions for a month or explicit date range and summarize
income, outflows, net cash flow, top spending categories, and notable
transactions.

This capability is factual read intelligence. It does not recommend budget
changes by itself; later brief and recommendation features can reuse its
structured output.

## When To Use

Use this capability when the user asks to:

- Review current month spending.
- Review previous month spending.
- Inspect transactions for a date range.
- Understand income, outflows, or net cash flow.
- Find top spending categories or notable transactions.

## Usage

Current month:

```powershell
python agents\njord\agent.py ynab-spending-review
```

Previous month:

```powershell
python agents\njord\agent.py ynab-spending-review --period previous-month
```

Explicit date range:

```powershell
python agents\njord\agent.py ynab-spending-review --from 2026-05-01 --to 2026-05-31
```

Natural-language routing:

```powershell
python agents\njord\agent.py ask "Review my current month spending."
```

## Output

The output includes:

- selected period.
- income.
- outflows.
- net cash flow.
- transaction count.
- previous-period comparison when matching prior transactions exist.
- top spending categories.
- notable transactions.

## Constraints

- Read-only.
- No live API calls in validation tests.
- Amounts are calculated from YNAB milliunits.
- Observations stay factual and separate from recommendations.
