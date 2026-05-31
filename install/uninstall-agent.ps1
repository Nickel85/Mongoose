<#
.SYNOPSIS
Removes the user-local Njord command installed by install-agent.ps1.
#>

[CmdletBinding()]
param(
    [string]$AgentName = "Njord"
)

$ErrorActionPreference = "Stop"

$installBin = Join-Path $env:LOCALAPPDATA "Agents\bin"
$launcherPath = Join-Path $installBin "$AgentName.cmd"

if (Test-Path $launcherPath) {
    Remove-Item -Path $launcherPath -Force
    Write-Host "Removed $launcherPath"
} else {
    Write-Host "$AgentName launcher was not found at $launcherPath"
}

Write-Host "The user PATH entry for $installBin was left in place in case other agents use it."

