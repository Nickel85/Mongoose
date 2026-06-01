# Capabilities

This directory contains the capabilities available to Njord.

Each capability should live in its own folder and include a `README.md` that explains its role, inputs, outputs, constraints, and examples.

## Available Capabilities

| Capability | Description |
| --- | --- |
| `hello-world` | Simple Python capability for verifying the agent can run a local tool. |
| `ynab-budget-summary` | Read YNAB budget data, summarize financial activity, and include review-needed flags. |

## Natural-Language Routing

Use the agent-level `ask` command to let Njord choose the capability:

```powershell
python agents\njord\agent.py ask "Hey Njord, get me my latest budget."
```

Current routing behavior:

- Budget, money, spending, financial, account, cash, YNAB, latest, review, attention, and summary requests route to `ynab-budget-summary`.
- Greeting, hello, test, and connection requests route to `hello-world`.
- Unknown requests default to `ynab-budget-summary` because this agent is finance-focused.

