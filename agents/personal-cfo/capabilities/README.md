# Capabilities

This directory contains the capabilities available to Personal CFO.

Each capability should live in its own folder and include a `README.md` that explains its role, inputs, outputs, constraints, and examples.

## Available Capabilities

| Capability | Description |
| --- | --- |
| `hello-world` | Simple Python capability for verifying the agent can run a local tool. |
| `ynab-budget-summary` | Read YNAB budget data and summarize financial activity. |

## Natural-Language Routing

Use the agent-level `ask` command to let Personal CFO choose the capability:

```powershell
python agents\personal-cfo\agent.py ask "Hey Nick, get me my latest budget."
```

Current routing behavior:

- Budget, money, spending, financial, account, cash, YNAB, latest, and summary requests route to `ynab-budget-summary`.
- Greeting, hello, test, and connection requests route to `hello-world`.
- Unknown requests default to `ynab-budget-summary` because this agent is finance-focused.
