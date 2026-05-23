# Agent Name

## Purpose

Describe what this agent is for and the kinds of tasks it should handle.

## Behavior

Describe the agent's working style, boundaries, assumptions, and any important decision rules.

## Dependencies

List any tools, services, credentials, models, files, or runtime dependencies required by this agent.

## Install Metadata

Each installable agent should include an `agent.json` manifest. The root installer discovers agents automatically by scanning `agents/*/agent.json`.

```json
{
  "commandName": "AgentName",
  "displayName": "Agent Display Name",
  "entrypointPath": "agent.py",
  "example": "Natural-language request here",
  "description": "Short description of what this agent does."
}
```

The `commandName` is the command users pass to `install.cmd` and the command that gets installed in the user-local bin directory.

`commandName` must be unique across all agents. `entrypointPath` is relative to this agent directory, so `agent.py` is fine even when other agents also have their own `agent.py`.

## Capabilities

Document the capabilities this agent contains.

| Capability | Description |
| --- | --- |
| `capability-name` | Short description of what the capability does. |

## Usage

Explain how to run, invoke, or work with this agent.

Preferred command-line shape:

```powershell
python agents\<agent-name>\agent.py ask "Natural-language request here."
```

Direct capability commands can also be documented here when useful:

```powershell
python agents\<agent-name>\agent.py <capability-name>
```

## Routing

Explain how natural-language requests map to capabilities. If the agent has a `router.py`, document the major routing keywords, defaults, and fallback behavior.

## Notes

Add implementation notes, known limitations, or maintenance guidance.
