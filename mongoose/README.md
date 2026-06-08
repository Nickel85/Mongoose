# Mongoose

Mongoose is the local-first capability runtime CLI for this agent repository.
It decouples AI functionality from underlying models, tools, storage, APIs, and
execution environments while still providing lifecycle commands for installing,
updating, and running agents.

The long-term goal is to make agents portable, reusable, and easy to manage
throughout their lifecycle. In that vision, agents declare the capabilities
they require, including LLMs, memory, tools, storage, and configured APIs, and
Mongoose provides those capabilities through a common interface so the same
agent can run on a personal laptop, enterprise workstation, or server without
modification.

That vision is not fully implemented yet. The sections below distinguish what
Mongoose does today from committed roadmap work and longer-term platform goals.

It installs as:

```text
mongoose
```

## Current Capabilities

Mongoose currently provides a Windows-focused, user-local CLI for installing
and running agents from this repository. It can:

- list available agents
- install an agent command from the configured registry or a local agent path
- inspect installed agent metadata and capabilities
- validate agent manifests without importing agent code
- enumerate and route across installed capabilities by task type
- run an installed agent entrypoint
- remove an installed agent command and state
- update the local agent registry from GitHub
- initialize and inspect user-local Mongoose state

Check the CLI version:

```powershell
mongoose --version
```

Development/source builds report as `development`. Executables built by the
GitHub release workflow from a matching `v*` tag report as `official release`
and include the tag.

Human-readable Mongoose and Njord output uses terminal color when stdout is an
interactive terminal. Redirected output stays plain by default, and JSON output
is never colorized. Disable color explicitly with:

```powershell
mongoose --no-color state
Njord --no-color brief
```

Color can also be disabled with `NO_COLOR=1`, `MONGOOSE_NO_COLOR=1`, or
`NJORD_NO_COLOR=1`. For troubleshooting captured output, force color with
`MONGOOSE_FORCE_COLOR=1` or `NJORD_FORCE_COLOR=1`.

Show local state, registry path, and registry revision diagnostics:

```powershell
mongoose state
mongoose state --json
```

Implemented agent metadata includes manifest schema validation, local entrypoint
resolution, command-name uniqueness, declared capability metadata, required
configuration names, compatibility metadata, and descriptive LLM metadata.

Implemented routing is deterministic. It selects installed capabilities from
manifest metadata and dispatches through the current subprocess entrypoint
shape. Mongoose does not yet provide a portable runtime context, common
provider interfaces, managed dependency isolation, or cross-platform execution
guarantees.

## Roadmap

Mongoose is being developed in layers so current agents remain useful while the
runtime grows toward the broader platform vision:

- Provider-neutral LLM runtime configuration and invocation are tracked in
  [#23](https://github.com/Nickel85/Mongoose/issues/23).
- Event-based and timer-based scheduling are tracked in
  [#1](https://github.com/Nickel85/Mongoose/issues/1) and
  [#2](https://github.com/Nickel85/Mongoose/issues/2).
- Agent job and status commands are tracked in
  [#4](https://github.com/Nickel85/Mongoose/issues/4), with persistent scheduler
  runtime work in [#5](https://github.com/Nickel85/Mongoose/issues/5).
- Cross-platform runtime support is tracked in
  [#38](https://github.com/Nickel85/Mongoose/issues/38).
- Agent dependency and environment isolation are tracked in
  [#39](https://github.com/Nickel85/Mongoose/issues/39).
- Package registry and versioning are tracked in
  [#40](https://github.com/Nickel85/Mongoose/issues/40).
- A portable agent execution contract is tracked in
  [#41](https://github.com/Nickel85/Mongoose/issues/41).
- Common capability provider interfaces for memory, storage, tools, and
  configured APIs are tracked in
  [#42](https://github.com/Nickel85/Mongoose/issues/42).

## Platform Direction

Mongoose's platform direction is local-first agent lifecycle management:
install, configure, discover, execute, update, route, observe, and remove
agents through a consistent runtime surface.

The intended future agent contract is provider-neutral. Agents should be able
to ask Mongoose for declared capabilities such as LLM profiles, durable memory,
local storage, tool invocation, external API profiles, logs, and job context
without binding themselves to a single host environment or secret layout.

Njord is the first concrete agent use case, not the whole platform. The Njord
roadmap is expected to prove useful deterministic financial workflows, including
the manual weekly brief tracked in
[#28](https://github.com/Nickel85/Mongoose/issues/28), while Mongoose separately
adds the package, scheduling, provider, capability, and portability features
needed for agents to run consistently across environments.

This sequencing is intentional. Agent-value milestones validate what the
platform actually needs; Mongoose platform milestones then generalize those
needs into reusable runtime features.

## Command Summary

The CLI can:

- list available agents
- install an agent command from the configured registry or a local agent path
- inspect installed agent metadata and capabilities
- enumerate and route across installed capabilities by task type
- run an installed agent entrypoint
- remove an installed agent command and state
- update the local agent registry from GitHub

## Build The EXE

From the repository root:

```text
.\build-mongoose.cmd
```

This generates:

```text
dist\mongoose.exe
```

The build currently uses `gcc` on Windows.

GitHub Actions also builds `mongoose.exe` for pull requests targeting `main`, pushes to `main`, and version tags. PR builds upload the executable as an Actions artifact. Tag builds attach it to the GitHub Release.

## Install Mongoose

From the repository root:

```text
.\install-mongoose.cmd
```

This copies:

```text
dist\mongoose.exe
```

to:

```text
%LOCALAPPDATA%\Agents\bin\mongoose.exe
```

It also copies the Python CLI implementation to:

```text
%LOCALAPPDATA%\Agents\mongoose\mongoose.py
```

The installer adds `%LOCALAPPDATA%\Agents\bin` to the current user's `PATH`. Open a new terminal after installing.

No administrator privileges are required.

## Commands

List available agents:

```powershell
mongoose list
```

List installed agents:

```powershell
mongoose list --installed
```

Install an agent:

```powershell
mongoose install Njord
```

Install an agent directly from a local package path:

```powershell
mongoose install C:\path\to\agent
```

Show installed metadata and discovered capabilities:

```powershell
mongoose show Njord
```

List routeable installed capabilities:

```powershell
mongoose capabilities
```

Route a request to an installed capability:

```powershell
mongoose route --task-type budget-summary "current budget"
mongoose route "summarize my current budget"
mongoose route --task-type budget-summary --dry-run
```

Validate manifests:

```powershell
mongoose validate
mongoose validate agents\njord
```

Run an installed agent entrypoint through Mongoose:

```powershell
mongoose run Njord config status
mongoose run Njord ask "Get me my latest budget"
```

Remove an installed agent:

```powershell
mongoose remove Njord
```

`mongoose uninstall Njord` remains available as an alias.

Pull down registry updates:

```powershell
mongoose update
```

`mongoose update` runs a two-phase update flow:

- refresh the configured registry path.
- check the installed Mongoose CLI against GitHub Releases.

If the registry is a Git checkout, Mongoose runs `git pull --ff-only`. If the
configured registry path does not exist, it clones the configured GitHub
registry URL. The command prints each phase and an update summary so registry
and CLI status are distinct.

Run only the registry phase:

```powershell
mongoose update --registry-only
```

Update the installed Mongoose CLI:

```powershell
mongoose update --self-only
```

`mongoose update --self-only` checks GitHub Releases for the latest stable
`Nickel85/Mongoose` release, compares it with the installed CLI version,
downloads the released `mongoose.exe` asset when a newer version is available,
and replaces the user-local executable under `%LOCALAPPDATA%\Agents\bin`.
Prereleases are ignored unless `--include-prerelease` is passed. The older
`mongoose update --self` spelling remains available as an alias.

After pulling registry changes, rerun `mongoose install <agent>` to refresh
installed agent metadata and launchers from the current registry. Local
contributors can still use `build-mongoose.cmd` and `install-mongoose.cmd` for
development builds.

Show the user-local state contract:

```powershell
mongoose state
mongoose state --init --json
```

`mongoose state --init` creates the shared no-admin directory layout under `%LOCALAPPDATA%\Agents`.
`mongoose state` also reports the Mongoose CLI version, CLI source path,
configured registry URL/path, registry Git revision when available, and whether
the registry checkout is clean, dirty, missing, or not a Git checkout.

## Local State

Mongoose keeps user-local state outside the repository so install metadata, runtime files, logs, and future agent configuration do not need administrator access and do not get committed by accident.

The shared layout is:

```text
%LOCALAPPDATA%\Agents\
  bin\                 Installed command shims and mongoose.exe
  mongoose\            Mongoose CLI config and registry metadata
    config.json        Registry configuration
    registry\Mongoose\ Default cloned registry location
  state\
    config\            Non-secret shared configuration
    agents\            Installed agent metadata and agent-scoped local state
    jobs\              Future job metadata
  logs\                JSONL logs
```

Only non-secret configuration belongs under `state\config`. Access tokens, API keys, passwords, and other credentials should stay in environment variables or future secret storage. Mongoose redacts secret-like keys and `token=value` style text before writing structured logs.

Logs are JSONL files under `%LOCALAPPDATA%\Agents\logs`. Use `mongoose state --cleanup-logs` to remove log files older than the default 30-day retention window. Pass `--log-retention-days <days>` to use a different retention window.

To reset local Mongoose state, uninstall agent commands first if needed, then remove `%LOCALAPPDATA%\Agents`. Reinstall with `install-mongoose.cmd` or rerun `mongoose setup`.

## Registry

Mongoose reads installable agents from:

```text
agents\*\agent.json
```

Each manifest provides the installed command name and local entrypoint for that agent.

When an agent is installed, Mongoose writes a small installed-agent record under:

```text
%LOCALAPPDATA%\Agents\state\agents\<commandName>.json
```

That record stores the manifest, source path, entrypoint, launcher path, install timestamp, version, and discovered capability metadata. It does not copy or delete the source package. `mongoose remove <agent>` removes the launcher and installed-agent record only.

Capabilities are discovered from a manifest `capabilities` array when present. If the manifest does not declare capabilities yet, Mongoose falls back to listing folders under `capabilities\`. The richer manifest contract is tracked separately in issue #26.

## Capability Routing

`mongoose route` is the deterministic Mongoose orchestrator. It reads installed-agent records from `%LOCALAPPDATA%\Agents\state\agents`, enumerates declared capabilities, and selects one capability without importing agent code.

Selection works in this order:

- `--agent` and `--capability` restrict the candidate set when provided.
- `--task-type <type>` matches declared capability `taskTypes`; agent-level `taskTypes` are used as fallback metadata for each capability.
- Without `--task-type`, Mongoose scores the request text against capability names, display names, descriptions, and task types.
- If exactly one installed capability matches, Mongoose dispatches to that capability.
- If multiple capabilities tie, Mongoose reports an ambiguous request and asks for `--agent`, `--capability`, or a more specific `--task-type`.
- If nothing matches, Mongoose lists installed capabilities so the user can see what is currently routeable.

Before dispatching, Mongoose checks that required environment-backed configuration is present and that the selected capability does not require an unavailable LLM runtime. Dispatch uses this stable invocation shape:

```text
python <capability entrypoint> <capability name> <request arguments...>
```

Capability-specific `entrypointPath` overrides the agent default entrypoint. `--dry-run` prints the selected capability, entrypoint, and argument vector without executing agent code.

## Runtime Contract

Mongoose Runtime Contract v1 lets agents discover host state and provider
availability without reading Mongoose internals. Existing agent arguments remain
stable, and Mongoose adds:

```text
MONGOOSE_RUNTIME_CONTEXT=<path-to-json-context>
MONGOOSE_RUNTIME_CONTRACT_VERSION=1
```

The context file includes invocation metadata, selected agent and capability
metadata, user-local state paths, provider descriptors, and structured runtime
error metadata. Provider descriptors currently include configuration, logs,
state, local storage, memory, tools, API profiles, and LLM. Secret values are
never written to manifests, logs, job metadata, package directories, or runtime
context files.

See [Runtime Contract v1](../docs/runtime-contract.md) for the full contract and
provider interface design.

## Manifest Contract

Mongoose reads `agent.json` without importing agent code. Current manifests are backward-compatible with the original required fields and may opt into richer metadata with `schemaVersion: 1`.

Required fields:

```json
{
  "commandName": "Njord",
  "displayName": "Njord",
  "entrypointPath": "agent.py",
  "example": "Get me my latest budget",
  "description": "Personal finance agent for YNAB budget analysis and financial summaries."
}
```

Recommended metadata:

```json
{
  "schemaVersion": 1,
  "id": "njord",
  "version": "0.1.0",
  "entrypoints": {
    "default": "agent.py"
  },
  "taskTypes": ["finance", "budget", "ynab"],
  "requiredInputs": ["YNAB_ACCESS_TOKEN", "YNAB_BUDGET_ID"],
  "configuration": {
    "required": ["YNAB_ACCESS_TOKEN", "YNAB_BUDGET_ID"],
    "optional": [],
    "secretRefs": ["YNAB_ACCESS_TOKEN"]
  },
  "compatibility": {
    "platforms": ["windows"],
    "python": ">=3.11",
    "mongooseManifestSchema": 1,
    "mongooseRuntimeContract": 1
  },
  "requires": {
    "state": { "mode": "required" },
    "logs": { "mode": "optional" },
    "storage": { "mode": "optional" }
  },
  "llm": {
    "mode": "none",
    "deterministicFallback": "All current capabilities run without an LLM."
  },
  "capabilities": [
    {
      "name": "ynab-budget-summary",
      "displayName": "YNAB Budget Summary",
      "description": "Read YNAB data and summarize the current budget state.",
      "entrypointPath": "agent.py",
      "taskTypes": ["finance", "budget-summary", "ynab"],
      "requiredInputs": ["YNAB_ACCESS_TOKEN", "YNAB_BUDGET_ID"],
      "configuration": {
        "required": ["YNAB_ACCESS_TOKEN", "YNAB_BUDGET_ID"],
        "optional": [],
        "secretRefs": ["YNAB_ACCESS_TOKEN"]
      },
      "requires": {
        "configuration": { "mode": "required" },
        "logs": { "mode": "optional" },
        "storage": { "mode": "optional" },
        "llm": { "mode": "optional" }
      },
      "llm": {
        "mode": "none",
        "deterministicFallback": "Summary uses deterministic reads and calculations."
      }
    }
  ]
}
```

LLM metadata is descriptive only at this layer. Provider credentials and API keys must not be stored in manifests. Agents should reference configuration names or future Mongoose LLM profile names; actual secrets belong in environment variables or future Mongoose secret/profile storage.

Schema version policy:

- Keep `schemaVersion` unchanged for additive optional metadata that older Mongoose versions can ignore safely.
- Increment `schemaVersion` for breaking manifest contract changes: new required fields, renamed or removed fields, changed field types or meanings, changed entrypoint invocation semantics, changed capability routing semantics, or required configuration/LLM contract changes.
- Update `SUPPORTED_MANIFEST_SCHEMA_VERSION`, this policy, the manifest examples, and the validation tests in the same change that introduces a breaking manifest contract.
- Mongoose rejects manifests with a `schemaVersion` newer than it supports, so agent authors get an explicit compatibility failure instead of a confusing install or runtime error.

Invalid manifests fail `mongoose validate`, registry listing, installation, or show commands with actionable errors. Mongoose validates relative entrypoints, capability metadata shape, supported schema versions, and obvious secret-bearing keys.

