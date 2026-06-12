# Capabilities

This directory contains the capabilities available to Njord.

Each capability should live in its own folder and include a `README.md` that explains its role, inputs, outputs, constraints, and examples.

## Available Capabilities

| Capability | Description |
| --- | --- |
| `brief` | Produce a weekly-style financial brief with observations, spending highlights, review items, and suggested next actions. |
| `hello-world` | Simple Python capability for verifying the agent can run a local tool. |
| `ynab-budget-summary` | Read YNAB budget data, summarize financial activity, and include review-needed flags. |
| `ynab-spending-review` | Review income, outflows, net cash flow, top categories, and notable transactions for a month or date range. |

## Natural-Language Routing

Use the Njord session to let Njord choose the capability:

```powershell
python agents\njord\agent.py
Njord> Hey Njord, get me my latest budget.
```

For scripts, tests, and Mongoose dispatch, the `ask` command remains available:

```powershell
python agents\njord\agent.py ask "Hey Njord, get me my latest budget."
```

Current routing behavior:

- Weekly brief, CFO-style brief, and financial brief requests route to `brief`.
- Spending, transaction, cash flow, income, outflow, current month, and previous month requests route to `ynab-spending-review`.
- Budget, money, financial, account, cash, YNAB, latest, review-needed, attention, and summary requests route to `ynab-budget-summary`.
- Greeting, hello, test, and connection requests route to `hello-world`.
- Unknown requests default to `ynab-budget-summary` because this agent is finance-focused.

