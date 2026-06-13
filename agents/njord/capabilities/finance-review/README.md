# Finance Review

`finance-review` runs Njord's interaction-first finance review. It composes
read-only AI capability loops for cash-flow forecasting and financial risk.

## Role

The capability turns a YNAB snapshot into deterministic fact packets, asks the
configured Mongoose LLM backend for structured read-only judgment when
available, validates the LLM decision contract, and prints a REPL-friendly
review. It does not write to YNAB.

## Inputs

- `YNAB_ACCESS_TOKEN`
- `YNAB_BUDGET_ID`
- Read-only YNAB accounts, categories, months, transactions, and scheduled
  transactions.

## Outputs

- cash-flow forecast facts.
- financial risk score and risk drivers.
- fact packet identifiers.
- decision-contract validation summary.
- validated LLM decision or an explicit unavailable/invalid-backend diagnostic.
- guardrails and next actions.

## Examples

```powershell
Njord
Njord> Review my finances.
```

For automation:

```powershell
python agents\njord\agent.py finance-review
mongoose run Njord finance-review
```

Natural-language routing also works:

```powershell
Njord> review my finances
```

## Constraints

- The loop is read-only.
- The LLM may explain validated facts but cannot calculate balances or approve
  writes.
- If the configured LLM backend is missing or returns unstructured text, the
  deterministic review still renders and reports the LLM decision as
  unavailable.
- Budget-changing requests remain draft-only until guarded write planning and
  execution are implemented.
