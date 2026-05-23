# Capability Name

## Purpose

Describe what this capability enables the agent to do.

## When To Use

Describe the situations where this capability should be selected.

## Inputs

List the expected inputs, files, context, or user information needed.

## Outputs

Describe the expected result, artifact, response, or side effect.

## Workflow

1. Describe the first step.
2. Describe the next step.
3. Describe how the capability completes.

## Usage

Document how to call this capability through the agent runner:

```powershell
python agents\<agent-name>\agent.py <capability-name>
```

If this capability can be selected by natural-language routing, include example prompts:

```powershell
python agents\<agent-name>\agent.py ask "Natural-language request here."
```

## Constraints

Document limits, safety rules, assumptions, or dependencies.

## Examples

Add short examples of requests or tasks this capability should handle.
