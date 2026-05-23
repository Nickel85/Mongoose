# Agents Directory

This directory contains one folder per agent.

Use `agents/_template/` as the starting point for a new agent. Each agent should document its purpose, expected behavior, dependencies, and capability list in its own `README.md`.

## Agent Layout

```text
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

## Running Agents

Agents that expose a command-line runner should be called from the repository root:

```powershell
python agents\<agent-name>\agent.py ask "Natural-language request here."
```

The `ask` command should route the request to the appropriate capability.
