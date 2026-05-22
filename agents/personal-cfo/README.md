# Personal CFO

## Purpose

Personal CFO is an agent for understanding and improving personal finances. It starts as an accountant for YNAB budget data: summarizing balances, spending, cash flow, category activity, and financial changes over time.

Over time, this agent should grow from reporting what happened into explaining why it happened and recommending what to do next.

## Behavior

Personal CFO should be:

- Accurate before clever.
- Clear about assumptions, missing data, and uncertainty.
- Conservative with recommendations that affect money.
- Respectful of privacy and careful with credentials.
- Practical, using plain-language summaries and specific numbers.

The agent should separate observations from recommendations. It should not make irreversible financial decisions, move money, or modify a budget unless that capability is explicitly added and approved.

## Dependencies

- YNAB account access.
- YNAB API token or OAuth access token.
- Selected YNAB budget or plan ID.
- Secure local configuration for secrets.
- A runtime capable of making HTTPS requests to the YNAB API.

YNAB API documentation: [https://api.ynab.com/](https://api.ynab.com/)

## Local Configuration

Store local secrets in a `.env` file at the repository root. This file is ignored by Git.

Start by copying `.env.example` to `.env`, then fill in:

```env
YNAB_ACCESS_TOKEN=
YNAB_BUDGET_ID=
```

Never commit the real `.env` file or paste the YNAB access token into documentation, logs, examples, or prompts.

## Capabilities

| Capability | Description |
| --- | --- |
| `hello-world` | Run a simple Python greeting capability to verify the agent runtime pattern works. |
| `ynab-budget-summary` | Read YNAB budget data and summarize current financial position, spending, category activity, and notable changes. |

## Usage

Ask this agent for budget summaries, spending reviews, category analysis, cash-flow snapshots, or questions about where money is going.

Example requests:

- "Summarize my budget this month."
- "Show me my biggest spending categories."
- "What changed since last month?"
- "Are there categories I should review?"
- "Give me a CFO-style weekly financial brief."

## Run The Agent

Run agent capabilities through `agent.py`.

From the repository root:

```powershell
python agents\personal-cfo\agent.py hello-world
```

With a custom name:

```powershell
python agents\personal-cfo\agent.py hello-world --name "Nick"
```

The `hello-world` capability also tests the YNAB API connection by loading `YNAB_ACCESS_TOKEN` from the repository root `.env` file and calling the YNAB plans endpoint.

If the token is configured correctly, the command reports that the connection succeeded and shows how many plans were found. It does not print the token.

To see available options:

```powershell
python agents\personal-cfo\agent.py --help
```

## Run The Sample Capability Directly

The `hello-world` capability is the first executable Python capability for this agent.

From the repository root, run:

```powershell
python agents\personal-cfo\capabilities\hello-world\hello_world.py
```

With a custom name:

```powershell
python agents\personal-cfo\capabilities\hello-world\hello_world.py --name "Nick"
```

Expected output:

```text
Hello, Nick.
Personal CFO is ready to review your financial life.
YNAB connection succeeded. Found 1 plan(s).
```

In VS Code, open a terminal from the repository root before running the command.

## Roadmap

1. Accountant mode: summarize financials from YNAB.
2. Analyst mode: identify patterns, anomalies, and trends.
3. Advisor mode: provide recommendations and tradeoffs.
4. Planner mode: forecast upcoming obligations and budget pressure.
5. Operator mode: optionally prepare YNAB updates for explicit approval.

## Notes

This agent should begin as read-only. Any future capability that writes to YNAB should be documented separately, require explicit confirmation, and prefer draft recommendations over automatic changes.
