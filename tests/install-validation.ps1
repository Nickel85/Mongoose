<#
.SYNOPSIS
Validates agent install metadata and no-admin installer behavior.
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$agentsRoot = Join-Path $repoRoot "agents"
$installCmd = Join-Path $repoRoot "install.cmd"
$installer = Join-Path $repoRoot "install\install-agent.ps1"

function Assert-True {
    param(
        [object]$Condition,
        [string]$Message
    )

    if (-not $Condition) {
        throw $Message
    }
}

function Read-AgentManifests {
    $manifests = @()

    $agentDirectories = Get-ChildItem -Path $agentsRoot -Directory | Where-Object {
        $_.Name -notlike "_*"
    }

    foreach ($agentDirectory in $agentDirectories) {
        $manifestPath = Join-Path $agentDirectory.FullName "agent.json"
        if (-not (Test-Path $manifestPath)) {
            continue
        }

        $manifest = Get-Content -Raw -Path $manifestPath | ConvertFrom-Json
        $manifests += [pscustomobject]@{
            AgentDirectory = $agentDirectory.FullName
            ManifestPath = $manifestPath
            Manifest = $manifest
        }
    }

    return $manifests
}

function Invoke-CommandAndCapture {
    param(
        [string]$FilePath,
        [string[]]$Arguments
    )

    $output = & $FilePath @Arguments 2>&1
    return [pscustomobject]@{
        ExitCode = $LASTEXITCODE
        Output = ($output | Out-String)
    }
}

Assert-True (Test-Path $installCmd) "install.cmd is missing."
Assert-True (Test-Path $installer) "install\install-agent.ps1 is missing."

$manifests = @(Read-AgentManifests)
Assert-True ($manifests.Count -gt 0) "No installable agents were discovered."

$commandNames = @{}
$entrypointsByCommandName = @{}
foreach ($entry in $manifests) {
    $manifest = $entry.Manifest
    $commandName = [string]$manifest.commandName
    $entrypointPathValue = [string]$manifest.entrypointPath

    Assert-True $commandName "Missing commandName in $($entry.ManifestPath)"
    Assert-True ($commandName -match "^[A-Za-z][A-Za-z0-9_-]*$") "Invalid commandName '$commandName' in $($entry.ManifestPath)"
    Assert-True (-not $commandNames.ContainsKey($commandName)) "Duplicate commandName '$commandName'"
    $commandNames[$commandName] = $entry.ManifestPath

    Assert-True ([string]$manifest.displayName) "Missing displayName in $($entry.ManifestPath)"
    Assert-True $entrypointPathValue "Missing entrypointPath in $($entry.ManifestPath)"
    Assert-True (-not [System.IO.Path]::IsPathRooted($entrypointPathValue)) "entrypointPath must be relative in $($entry.ManifestPath)"
    Assert-True ([string]$manifest.example) "Missing example in $($entry.ManifestPath)"
    Assert-True ([string]$manifest.description) "Missing description in $($entry.ManifestPath)"

    $entrypointPath = Join-Path $entry.AgentDirectory $entrypointPathValue
    Assert-True (Test-Path $entrypointPath) "Entrypoint does not exist: $entrypointPath"
    $resolvedEntrypoint = (Resolve-Path $entrypointPath).Path
    $resolvedAgentDirectory = (Resolve-Path $entry.AgentDirectory).Path
    Assert-True $resolvedEntrypoint.StartsWith($resolvedAgentDirectory) "Entrypoint must stay inside its agent directory: $entrypointPath"
    $entrypointsByCommandName[$commandName] = $resolvedEntrypoint
}

$testLocalAppData = Join-Path $repoRoot ".test-localappdata"
if (Test-Path $testLocalAppData) {
    Remove-Item -Path $testLocalAppData -Recurse -Force
}
New-Item -ItemType Directory -Path $testLocalAppData -Force | Out-Null
$env:LOCALAPPDATA = $testLocalAppData

$unknown = Invoke-CommandAndCapture -FilePath $installCmd -Arguments @("DefinitelyMissingAgent")
Assert-True ($unknown.ExitCode -ne 0) "Unknown agent install unexpectedly succeeded."
Assert-True ($unknown.Output -match "does not exist") "Unknown agent output did not explain the missing agent."
Assert-True ($unknown.Output -match "Available agents") "Unknown agent output did not list available agents."

foreach ($commandName in ($commandNames.Keys | Sort-Object)) {
    $result = Invoke-CommandAndCapture -FilePath $installCmd -Arguments @($commandName)
    Assert-True ($result.ExitCode -eq 0) "Install failed for $commandName. Output: $($result.Output)"

    $launcherPath = Join-Path $testLocalAppData "Agents\bin\$commandName.cmd"
    Assert-True (Test-Path $launcherPath) "Launcher was not created: $launcherPath"

    $launcher = Get-Content -Raw -Path $launcherPath
    Assert-True ($launcher.Contains($entrypointsByCommandName[$commandName])) "Launcher does not call the configured entrypoint."
    Assert-True ($launcher -match "\sask\s") "Launcher does not call the ask command."
}

Write-Host "Install validation passed for $($commandNames.Count) agent(s)."
