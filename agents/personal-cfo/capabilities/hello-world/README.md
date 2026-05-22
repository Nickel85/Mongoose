# Hello World

## Purpose

Provide a minimal Python capability that proves the Personal CFO agent can call a local program and connect to the YNAB API.

This capability is intentionally simple. It is the starting pattern for future executable capabilities that read configuration, call APIs, transform data, and return structured summaries.

## When To Use

Use this capability when:

- Verifying Python is available.
- Testing the agent capability folder pattern.
- Demonstrating how a capability can be invoked from the command line.
- Testing whether `YNAB_ACCESS_TOKEN` can authenticate with the YNAB API.
- Creating a baseline before adding YNAB API calls.

## Inputs

- Optional `--name` value for the person or context being greeted.
- `YNAB_ACCESS_TOKEN` from the repository root `.env` file.

## Outputs

- A short greeting printed to standard output.
- A reminder that Personal CFO is ready to review finances.
- YNAB API connection status.

## Usage

### Prerequisites

- Python 3 installed and available as `python`.
- Terminal opened at the repository root: `C:\Users\vnico\OneDrive\Documents\Agents`.

Verify Python is available:

```powershell
python --version
```

### Run From PowerShell

Preferred agent-level command from the repository root:

```powershell
python agents\personal-cfo\agent.py hello-world
```

With a custom name:

```powershell
python agents\personal-cfo\agent.py hello-world --name "Nick"
```

You can also run the capability directly:

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

If `.env` does not contain `YNAB_ACCESS_TOKEN`, the command exits with an error and tells you to add the token. The token is never printed.

### Run From VS Code

1. Open the repository folder in VS Code.
2. Open the integrated terminal with `Terminal > New Terminal`.
3. Confirm the terminal is at the repository root.
4. Run:

```powershell
python agents\personal-cfo\agent.py hello-world --name "Nick"
```

### Help

To see agent-level command options:

```powershell
python agents\personal-cfo\agent.py --help
```

To see direct capability options:

```powershell
python agents\personal-cfo\capabilities\hello-world\hello_world.py --help
```

## Constraints

- This capability reads `YNAB_ACCESS_TOKEN` from `.env`.
- This capability calls `https://api.ynab.com/v1/plans`.
- This capability does not modify files or financial data.
- This capability never prints the token.

## Next Steps

Use this capability as the smallest working example before building Python capabilities that load `.env`, query YNAB, and produce financial summaries.
