# Mongoose

Mongoose is the package-manager CLI for this agent repository.

It installs as:

```text
mongoose
```

The CLI can:

- list available agents
- install an agent command
- uninstall an agent command
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

Install an agent:

```powershell
mongoose install Midas
```

Uninstall an agent:

```powershell
mongoose uninstall Midas
```

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
    agents\            Agent-scoped local state
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
