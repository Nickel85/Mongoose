<#
.SYNOPSIS
Installs the Personal CFO agent as a user-local Nick command.

.DESCRIPTION
This installer does not require administrator privileges. It creates a Nick.cmd
launcher in %LOCALAPPDATA%\Agents\bin and adds that folder to the current user's
PATH if needed.
#>

[CmdletBinding()]
param(
    [string]$InstallName = "Nick"
)

$ErrorActionPreference = "Stop"

function Resolve-RepoRoot {
    $scriptPath = $PSCommandPath
    if (-not $scriptPath) {
        throw "Could not resolve installer path. Run this script from a file."
    }

    return (Resolve-Path (Join-Path (Split-Path -Parent $scriptPath) "..")).Path
}

function Get-PythonCommand {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        return "python"
    }

    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        return "py -3"
    }

    throw "Python was not found. Install Python 3 for your user account, then rerun this installer."
}

function Add-UserPath {
    param([string]$Directory)

    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $paths = @()
    if ($userPath) {
        $paths = $userPath -split ";" | Where-Object { $_ }
    }

    $alreadyPresent = $paths | Where-Object {
        $_.TrimEnd("\") -ieq $Directory.TrimEnd("\")
    }

    if (-not $alreadyPresent) {
        $updatedPath = (@($paths) + $Directory) -join ";"
        [Environment]::SetEnvironmentVariable("Path", $updatedPath, "User")
    }

    if (($env:Path -split ";") -notcontains $Directory) {
        $env:Path = "$env:Path;$Directory"
    }
}

$repoRoot = Resolve-RepoRoot
$agentPath = Join-Path $repoRoot "agents\personal-cfo\agent.py"
if (-not (Test-Path $agentPath)) {
    throw "Could not find Personal CFO agent at $agentPath"
}

$pythonCommand = Get-PythonCommand
$installBin = Join-Path $env:LOCALAPPDATA "Agents\bin"
New-Item -ItemType Directory -Path $installBin -Force | Out-Null

$launcherPath = Join-Path $installBin "$InstallName.cmd"
$launcher = @"
@echo off
$pythonCommand "$agentPath" ask %*
"@

Set-Content -Path $launcherPath -Value $launcher -Encoding ASCII
Add-UserPath -Directory $installBin

Write-Host "Installed $InstallName command."
Write-Host "Launcher: $launcherPath"
Write-Host "Agent: $agentPath"
Write-Host ""
Write-Host "Try it now:"
Write-Host "$InstallName `"Get me my latest budget`""
Write-Host ""
Write-Host "If a terminal cannot find $InstallName, close and reopen it so PATH refreshes."

