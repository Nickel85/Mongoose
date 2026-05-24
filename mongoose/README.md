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
mongoose install Nick
```

Uninstall an agent:

```powershell
mongoose uninstall Nick
```

Pull down registry updates:

```powershell
mongoose update
```

`mongoose update` uses the configured registry path. If the registry is a Git checkout, it runs `git pull --ff-only`. If the configured registry path does not exist, it clones the configured GitHub registry URL.

## Registry

Mongoose reads installable agents from:

```text
agents\*\agent.json
```

Each manifest provides the installed command name and local entrypoint for that agent.
