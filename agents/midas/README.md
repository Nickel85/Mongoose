# Midas

## Purpose

Midas is an agent for understanding and improving personal finances. It starts as an accountant for YNAB budget data: summarizing balances, spending, cash flow, category activity, and financial changes over time.

Over time, this agent should grow from reporting what happened into explaining why it happened and recommending what to do next.

## Behavior

Midas should be:

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

## YNAB Read Layer

Midas reads YNAB data through [ynab_api.py](ynab_api.py). Capabilities should use that shared module instead of making raw HTTP requests directly.

The read layer provides:

- one authenticated read-only client for the YNAB API.
- helpers for plans/budgets, accounts, categories, months, transactions, and scheduled transactions.
- deterministic plan selection when `YNAB_BUDGET_ID` is configured.
- consistent milliunit currency formatting and ISO date parsing.
- structured, user-facing errors for missing tokens, rejected tokens, HTTP failures, malformed JSON, URL failures, and timeouts.
- token-safe error handling that avoids printing access tokens or authorization details.

The current YNAB API uses `plans` as the primary resource name. Midas still accepts budget-oriented language in configuration and user-facing text because users commonly think in terms of budgets.

## Install

Install Midas as the user-local `Midas` command without administrator privileges.

Preferred package-manager flow:

```powershell
mongoose install Midas
```

If Mongoose is not installed yet, build and install it from the repository root:

```text
.\build-mongoose.cmd
.\install-mongoose.cmd
```

Legacy direct installer:

From the repository root:

```text
.\install.cmd Midas
```

All agents use `.\install.cmd <agent-install-name>`. Midas's install name is `Midas`. If an agent does not exist, the installer prints the available agent names.

The installer discovers this agent from [agent.json](agent.json):

```json
{
  "commandName": "Midas",
  "displayName": "Midas",
  "entrypointPath": "agent.py",
  "example": "Get me my latest budget",
  "description": "Personal finance agent for YNAB budget analysis and financial summaries."
}
```

The installer creates:

```text
%LOCALAPPDATA%\Agents\bin\Midas.cmd
```

It also adds that folder to the current user's `PATH`. Open a new terminal after installing.

Then run:

```powershell
Midas "Get me my latest budget"
```

Unquoted requests work too:

```powershell
Midas Get me my latest budget
```

If the current terminal cannot find `Midas` yet, open a new terminal or call the launcher directly:

```powershell
& "$env:LOCALAPPDATA\Agents\bin\Midas.cmd" "Get me my latest budget"
```

For installer internals, update notes, and uninstall instructions, see [../../install/README.md](../../install/README.md).

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
python agents\midas\agent.py ask "Hey Midas, get me my latest budget."
```

The `ask` command routes natural-language requests to the best available capability.

You can also call capabilities directly:

```powershell
python agents\midas\agent.py hello-world
```

With a custom name:

```powershell
python agents\midas\agent.py hello-world --name "Midas"
```

Latest budget summary:

```powershell
python agents\midas\agent.py ynab-budget-summary
```

After running the user-local installer, you can call this agent from any new terminal:

```powershell
Midas "Get me my latest budget"
```

The `hello-world` capability also tests the YNAB API connection by loading `YNAB_ACCESS_TOKEN` from the repository root `.env` file and calling the YNAB plans endpoint.

If the token is configured correctly, the command reports that the connection succeeded and shows how many plans were found. It does not print the token.

To see available options:

```powershell
python agents\midas\agent.py --help
```

## Run The Sample Capability Directly

The `hello-world` capability is the first executable Python capability for this agent.

From the repository root, run:

```powershell
python agents\midas\capabilities\hello-world\hello_world.py
```

With a custom name:

```powershell
python agents\midas\capabilities\hello-world\hello_world.py --name "Midas"
```

Expected output:

```text
Hello, Midas.
Midas is ready to review your financial life.
YNAB connection succeeded. Found <count> plan(s).
```

In VS Code, open a terminal from the repository root before running the command.

## Internal Structure

- `agent.py`: Command-line entrypoint.
- `agent.json`: Install metadata discovered by the root installer. Its `commandName` is globally unique; its `entrypointPath` is relative to this directory.
- `router.py`: Routes natural-language requests to capabilities.
- `config.py`: Loads local environment values from `.env`.
- `ynab_api.py`: Shared read-only YNAB API client and normalization helpers.
- `capabilities/`: Capability implementations and documentation.

## Roadmap

1. Accountant mode: summarize financials from YNAB.
2. Analyst mode: identify patterns, anomalies, and trends.
3. Advisor mode: provide recommendations and tradeoffs.
4. Planner mode: forecast upcoming obligations and budget pressure.
5. Operator mode: optionally prepare YNAB updates for explicit approval.

## Notes

This agent should begin as read-only. Any future capability that writes to YNAB should be documented separately, require explicit confirmation, and prefer draft recommendations over automatic changes.
