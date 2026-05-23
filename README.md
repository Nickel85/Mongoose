# Agents

Repository of agents for personal use.

## Structure

Each agent lives in its own directory under `agents/`. An agent directory should contain a `README.md` that explains the agent's purpose, operating notes, dependencies, and how to use it.

Capabilities for an agent live under that agent's `capabilities/` directory. Each capability gets its own folder with a `README.md` describing what it does, when to use it, inputs, outputs, and any important constraints.

Executable agents should expose an `agent.py` entrypoint. The preferred pattern is to support an `ask` command that accepts a natural-language request, routes it to the best capability, and prints the result.

```text
agents/
  <agent-name>/
    agent.py
    README.md
    router.py
    config.py
    capabilities/
      <capability-name>/
        README.md
        <capability_program>.py
```

## Adding An Agent

1. Copy `agents/_template/` to `agents/<agent-name>/`.
2. Update the agent `README.md` with the agent's particulars.
3. Add capability folders under `agents/<agent-name>/capabilities/`.
4. Document each capability in its own `README.md`.
5. Add or update `agent.py` and `router.py` when capabilities should be callable from natural-language requests.

## Running An Agent

From the repository root, call an agent through its `agent.py` entrypoint:

```powershell
python agents\personal-cfo\agent.py ask "Hey Nick, get me my latest budget."
```

For direct capability calls:

```powershell
python agents\personal-cfo\agent.py ynab-budget-summary
```

## Install The Nick Command

Install the Personal CFO agent as a user-local `Nick` command without administrator privileges:

```text
.\install.cmd
```

Then open a new terminal and run:

```powershell
Nick "Get me my latest budget"
```

On a fresh machine, clone or download this repo first, then run `install.cmd` from the repo root.

See [install/README.md](install/README.md) for install, update, and uninstall details.

## VS Code Setup

This repository includes workspace settings in `.vscode/`.

Recommended first step:

1. Open the repository in VS Code.
2. Install the recommended extensions when prompted.
3. Run the task `Create local .env`.
4. Add local secret values to `.env`.

The `.env` file is ignored by Git. Commit `.env.example` only.

## Directory Guide

- `agents/`: All agent definitions.
- `agents/personal-cfo/`: Personal finance agent for analyzing YNAB budget data.
- `agents/personal-cfo/agent.py`: Personal CFO command-line entrypoint.
- `agents/personal-cfo/router.py`: Natural-language request router.
- `install.cmd`: One-file no-admin installer for the `Nick` command.
- `install/`: User-local installer scripts for commands like `Nick`.
- `agents/_template/`: Starter template for a new agent.
- `agents/_template/capabilities/_template/`: Starter template for a new capability.
