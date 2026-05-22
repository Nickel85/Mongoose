# Agents

Repository of agents for personal use.

## Structure

Each agent lives in its own directory under `agents/`. An agent directory should contain a `README.md` that explains the agent's purpose, operating notes, dependencies, and how to use it.

Capabilities for an agent live under that agent's `capabilities/` directory. Each capability gets its own folder with a `README.md` describing what it does, when to use it, inputs, outputs, and any important constraints.

```text
agents/
  <agent-name>/
    README.md
    capabilities/
      <capability-name>/
        README.md
```

## Adding An Agent

1. Copy `agents/_template/` to `agents/<agent-name>/`.
2. Update the agent `README.md` with the agent's particulars.
3. Add capability folders under `agents/<agent-name>/capabilities/`.
4. Document each capability in its own `README.md`.

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
- `agents/_template/`: Starter template for a new agent.
- `agents/_template/capabilities/_template/`: Starter template for a new capability.
