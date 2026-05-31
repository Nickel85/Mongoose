# Mongoose

Mongoose is the package-manager CLI for this agent repository.

It installs as:

```text
mongoose
```

The CLI can:

- list available agents
- install an agent command from the configured registry or a local agent path
- inspect installed agent metadata and capabilities
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

`mongoose update` uses the configured registry path. If the registry is a Git checkout, it runs `git pull --ff-only`. If the configured registry path does not exist, it clones the configured GitHub registry URL.

Show the user-local state contract:

```powershell
mongoose state
mongoose state --init --json
```

`mongoose state --init` creates the shared no-admin directory layout under `%LOCALAPPDATA%\Agents`.

## Local State

Mongoose keeps user-local state outside the repository so install metadata, runtime files, logs, and future agent configuration do not need administrator access and do not get committed by accident.

The shared layout is:

```text
%LOCALAPPDATA%\Agents\
  bin\                 Installed command shims and mongoose.exe
  mongoose\            Mongoose CLI config and registry metadata
    config.json        Registry configuration
    registry\Agents\   Default cloned registry location
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
    "mongooseManifestSchema": 1
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
      "llm": {
        "mode": "none",
        "deterministicFallback": "Summary uses deterministic reads and calculations."
      }
    }
  ]
}
```

LLM metadata is descriptive only at this layer. Provider credentials and API keys must not be stored in manifests. Agents should reference configuration names or future Mongoose LLM profile names; actual secrets belong in environment variables or future Mongoose secret/profile storage.

Invalid manifests fail `mongoose validate`, registry listing, installation, or show commands with actionable errors. Mongoose validates relative entrypoints, capability metadata shape, supported schema versions, and obvious secret-bearing keys.

