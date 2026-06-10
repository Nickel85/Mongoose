# Mongoose Architecture

Mongoose architecture artifacts are generated from repository metadata so the
visual diagrams and textual model stay aligned with the same source of truth.

The generation flow is:

```text
agents/*/agent.json
        -> Mongoose architecture model
        -> SysML v2 text views
        -> Mermaid diagram views
```

The shared model is committed at:

```text
docs/architecture/model.json
```

Generated views are committed at:

```text
docs/architecture/sysml/agents.sysml
docs/architecture/sysml/runtime-routing.sysml
docs/architecture/diagrams/agents.mmd
docs/architecture/diagrams/runtime-routing.mmd
docs/architecture/diagrams/providers.mmd
```

Do not edit generated files by hand. Update manifests or generator behavior,
then regenerate:

```powershell
python .\mongoose\mongoose.py architecture generate --root .
```

Validate that committed architecture artifacts are fresh:

```powershell
python .\mongoose\mongoose.py architecture validate --root .
```

## Viewing Diagrams

Mermaid files are lightweight diagram projections of the shared architecture
model. GitHub can render Mermaid in Markdown, and most editors can preview
`.mmd` files with a Mermaid extension.

The Mermaid diagrams do not parse SysML directly. SysML and Mermaid are sibling
outputs generated from `model.json`. SysML is the formal textual engineering
view; Mermaid is the practical visual view.

## Current Views

- `agents.sysml` and `agents.mmd` show installed-agent structure, entrypoints,
  capability declarations, task types, configuration requirements, and LLM mode.
- `runtime-routing.sysml` and `runtime-routing.mmd` show the request path from
  user input through manifest-based routing into a selected capability.
- `providers.mmd` shows implemented and planned Mongoose runtime provider
  surfaces.

## Validation

Architecture freshness is part of CI. If a manifest or generator change makes
these files stale, run the generation command and commit the resulting updates.
