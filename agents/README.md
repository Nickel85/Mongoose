# Agents Directory

This directory contains one folder per agent.

Use `agents/_template/` as the starting point for a new agent. Each agent should document its purpose, expected behavior, dependencies, and capability list in its own `README.md`.

## Agent Layout

```text
<agent-name>/
  agent.json
  agent.py
  README.md
  router.py
  config.py
  capabilities/
    <capability-name>/
      README.md
      <capability_program>.py
```

## Install Metadata

Installable agents include an `agent.json` manifest. The root installer discovers available agents by scanning `agents/*/agent.json`.

```json
{
  "commandName": "AgentName",
  "displayName": "Agent Display Name",
  "entrypointPath": "agent.py",
  "example": "Natural-language request here",
  "description": "Short description of what this agent does."
}
```

The `commandName` is passed to the shared root installer:

```text
.\install.cmd AgentName
```

`commandName` must be unique across all agents because it becomes the installed command. `entrypointPath` only needs to be valid inside that agent directory, so multiple agents can use `agent.py`.

## Running Agents

Agents that expose a command-line runner should be called from the repository root:

```powershell
python agents\<agent-name>\agent.py ask "Natural-language request here."
```

The `ask` command should route the request to the appropriate capability.
