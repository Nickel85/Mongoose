<#
.SYNOPSIS
Removes the user-local Nick command installed by install-nick.ps1.
#>

[CmdletBinding()]
param(
    [string]$InstallName = "Nick"
)

$ErrorActionPreference = "Stop"

$installBin = Join-Path $env:LOCALAPPDATA "Agents\bin"
$launcherPath = Join-Path $installBin "$InstallName.cmd"

if (Test-Path $launcherPath) {
    Remove-Item -Path $launcherPath -Force
    Write-Host "Removed $launcherPath"
} else {
    Write-Host "$InstallName launcher was not found at $launcherPath"
}

Write-Host "The user PATH entry for $installBin was left in place in case other agents use it."

