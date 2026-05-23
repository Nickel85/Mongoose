# Install

Install the Personal CFO agent as a user-local `Nick` command without administrator privileges.

## Requirements

- Windows PowerShell.
- Python 3 available as `python` or `py`.
- This repository available on the machine.
- A local `.env` file at the repository root for YNAB access.

## Install

From the repository root:

```text
.\install.cmd
```

You can also double-click `install.cmd` from File Explorer.

The one-file installer calls the PowerShell installer internally:

```powershell
powershell -ExecutionPolicy Bypass -File .\install\install-nick.ps1
```

The installer creates:

```text
%LOCALAPPDATA%\Agents\bin\Nick.cmd
```

It also adds that folder to the current user's `PATH`. No administrator privileges are required.

## Fresh Machine Setup

Clone or download this repository, then run the installer:

```powershell
git clone https://github.com/Nickel85/Agents.git
cd Agents
.\install.cmd
```

Create `.env` from the example and add your local values:

```powershell
Copy-Item .env.example .env
notepad .env
```

## Use

Open a new terminal, then run:

```powershell
Nick "Get me my latest budget"
```

Unquoted requests also work:

```powershell
Nick Get me my latest budget
```

Both commands call:

```powershell
python agents\personal-cfo\agent.py ask "Get me my latest budget"
```

If the current terminal cannot find `Nick` yet, either open a new terminal or call the launcher directly:

```powershell
& "$env:LOCALAPPDATA\Agents\bin\Nick.cmd" "Get me my latest budget"
```

## Update

Pull the latest repository changes. The installed launcher points at this repo's `agent.py`, so code updates are picked up automatically.

If you move the repository to another folder, rerun:

```text
.\install.cmd
```

## Uninstall

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\install\uninstall-nick.ps1
```
