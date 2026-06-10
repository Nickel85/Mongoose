# SysML Modeling Conventions

The SysML files in this directory are generated textual views of the Mongoose
architecture model. They are meant to make runtime structure, request behavior,
and agent variants explicit without forcing every project discussion through
source code.

## Source Of Truth

Agent manifests and Mongoose runtime metadata are the source inputs. The
generator builds `docs/architecture/model.json`, then renders SysML and Mermaid
views from that model.

Hand-authored design notes belong in Markdown files. Generated SysML files
should only be changed by running:

```powershell
python .\mongoose\mongoose.py architecture generate --root .
```

## Naming

- Runtime elements use `MongooseRuntime` or `runtime`.
- Agent parts use the manifest `id` when present, normalized to a SysML-safe
  identifier.
- Capability parts are nested under the owning agent and use
  `<agent>_<capability>`.
- External services are modeled separately from local runtime providers.

## Structure, Behavior, And Variants

Structural views answer what exists: agents, capabilities, entrypoints,
configuration names, task types, and provider needs.

Behavioral views answer how a request moves: user request, installed manifest
metadata, route selection, capability dispatch, local deterministic execution,
and external read-only API calls.

Variant views answer which operating mode is active. For Njord, useful variants
include:

- deterministic read-only finance review
- LLM-assisted explanation using a Mongoose LLM profile
- user-reviewed write recommendations
- auto-approved write actions above an explicit confidence threshold

Those variants should be represented as agent or capability modes, not as Git
branches.

## Branch Terms

Git branches are repository version-control snapshots. Do not model every Git
branch as a SysML element.

Router branches are behavior branches. They belong in runtime-routing views
because they show how Mongoose selects a capability such as `hello-world`,
`ynab-budget-summary`, `ynab-spending-review`, or `brief`.

Agent variants are runtime modes or maturity stages. They should be modeled as
configuration or behavioral variants when they change execution semantics,
provider requirements, review boundaries, or approval policy.

## Mermaid Relationship

Mermaid diagrams use the same generated architecture model as the SysML files.
Mermaid is the human-friendly diagram view. SysML is the formal textual model
view. Neither output should be treated as the sole source of truth.
