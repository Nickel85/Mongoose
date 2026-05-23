# Capabilities

This directory contains the capabilities available to this agent.

Each capability should live in its own folder and include a `README.md` that explains the capability's role, inputs, outputs, constraints, and examples.

Use `_template/` as the starting point for a new capability.

## Natural-Language Routing

If the agent supports `agent.py ask`, document which requests route to each capability:

```powershell
python agents\<agent-name>\agent.py ask "Natural-language request here."
```
