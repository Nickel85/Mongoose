<#
.SYNOPSIS
Installs a known agent as a user-local command.

.DESCRIPTION
This installer does not require administrator privileges. It creates an agent command
launcher in %LOCALAPPDATA%\Agents\bin and adds that folder to the current user's
PATH if needed.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$AgentName
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

function Get-AgentRegistry {
    param([string]$RepoRoot)

    $registry = @{}
    $agentsRoot = Join-Path $RepoRoot "agents"
    if (-not (Test-Path $agentsRoot)) {
        return $registry
    }

    Get-ChildItem -Path $agentsRoot -Directory | Where-Object {
        $_.Name -notlike "_*"
    } | ForEach-Object {
        $manifestPath = Join-Path $_.FullName "agent.json"
        if (-not (Test-Path $manifestPath)) {
            return
        }

        try {
            $manifest = Get-Content -Raw -Path $manifestPath | ConvertFrom-Json
        } catch {
            Write-Warning "Skipping invalid agent manifest: $manifestPath"
            return
        }

        $commandName = [string]$manifest.commandName
        $entrypointPath = [string]$manifest.entrypointPath
        if (-not $commandName -or -not $entrypointPath) {
            Write-Warning "Skipping manifest missing commandName or entrypointPath: $manifestPath"
            return
        }

        if ($commandName -notmatch "^[A-Za-z][A-Za-z0-9_-]*$") {
            Write-Warning "Skipping manifest with invalid commandName '$commandName': $manifestPath"
            return
        }

        $registry[$commandName] = @{
            CommandName = $commandName
            DisplayName = [string]$manifest.displayName
            AgentPath = Join-Path $_.FullName $entrypointPath
            Example = [string]$manifest.example
            Description = [string]$manifest.description
            ManifestPath = $manifestPath
        }
    }

    return $registry
}

function Show-AvailableAgents {
    param([hashtable]$Registry)

    Write-Host "Available agents:"
    foreach ($name in ($Registry.Keys | Sort-Object)) {
        $description = $Registry[$name].Description
        if ($description) {
            Write-Host "  $name - $description"
        } else {
            Write-Host "  $name"
        }
    }
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
$agents = Get-AgentRegistry -RepoRoot $repoRoot

if (-not $agents.ContainsKey($AgentName)) {
    Write-Host "Agent '$AgentName' does not exist."
    Write-Host ""
    Show-AvailableAgents -Registry $agents
    exit 1
}

$agent = $agents[$AgentName]
$commandName = $agent.CommandName
$agentPath = $agent.AgentPath
$example = $agent.Example
if (-not $example) {
    $example = "Hello"
}

if (-not (Test-Path $agentPath)) {
    throw "Could not find $AgentName agent at $agentPath"
}

$pythonCommand = Get-PythonCommand
$installBin = Join-Path $env:LOCALAPPDATA "Agents\bin"
New-Item -ItemType Directory -Path $installBin -Force | Out-Null

$launcherPath = Join-Path $installBin "$commandName.cmd"
$launcher = @"
@echo off
$pythonCommand "$agentPath" ask %*
"@

Set-Content -Path $launcherPath -Value $launcher -Encoding ASCII
Add-UserPath -Directory $installBin

Write-Host "Installed $AgentName agent as $commandName."
Write-Host "Launcher: $launcherPath"
Write-Host "Agent: $agentPath"
Write-Host ""
Write-Host "Try it now:"
Write-Host "$commandName `"$example`""
Write-Host ""
Write-Host "If a terminal cannot find $commandName, close and reopen it so PATH refreshes."
