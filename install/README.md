# Legacy Agent Install

Install a known agent as a user-local command without administrator privileges.

This folder contains the original direct agent installer. The preferred package-manager flow is now documented in [../mongoose/README.md](../mongoose/README.md).

## Requirements

- Windows PowerShell.
- Python 3 available as `python` or `py`.
- This repository available on the machine.
- A local `.env` file at the repository root for YNAB access.

## Install

From the repository root:

```text
.\install.cmd Midas
```

The install argument is the agent name. Currently available agents:

- `Midas`

The installer discovers available agents by scanning:

```text
agents\*\agent.json
```

Template directories beginning with `_` are ignored. If you pass a name that does not exist, the installer prints the available names and exits without installing anything.

An agent manifest looks like:

```json
{
  "commandName": "Midas",
  "displayName": "Midas",
  "entrypointPath": "agent.py",
  "example": "Get me my latest budget",
  "description": "Personal finance agent for YNAB budget analysis and financial summaries."
}
```

The `commandName` must be unique across all agents because it becomes the installed command. The `entrypointPath` is relative to that agent's directory, so each agent can use the same local filename, such as `agent.py`.

The one-file installer calls the PowerShell installer internally:

```powershell
powershell -ExecutionPolicy Bypass -File .\install\install-agent.ps1 -AgentName Midas
```

The installer creates:

```text
%LOCALAPPDATA%\Agents\bin\Midas.cmd
```

It also adds that folder to the current user's `PATH`. No administrator privileges are required.

## Fresh Machine Setup

Clone or download this repository, then run the installer:

```powershell
git clone https://github.com/Midasel85/Agents.git
cd Agents
.\install.cmd Midas
```

Create `.env` from the example and add your local values:

```powershell
Copy-Item .env.example .env
notepad .env
```

## Use

Open a new terminal, then run:

```powershell
Midas "Get me my latest budget"
```

Unquoted requests also work:

```powershell
Midas Get me my latest budget
```

Both commands call:

```powershell
python agents\midas\agent.py ask "Get me my latest budget"
```

If the current terminal cannot find `Midas` yet, either open a new terminal or call the launcher directly:

```powershell
& "$env:LOCALAPPDATA\Agents\bin\Midas.cmd" "Get me my latest budget"
```

## Update

Pull the latest repository changes. The installed launcher points at this repo's `agent.py`, so code updates are picked up automatically.

If you move the repository to another folder, rerun:

```text
.\install.cmd Midas
```

## Uninstall

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\install\uninstall-agent.ps1
```
