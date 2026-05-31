<#
.SYNOPSIS
Validates the mongoose package manager CLI behavior without requiring a compiler.
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$mongooseCli = Join-Path $repoRoot "mongoose\mongoose.py"
$testLocalAppData = Join-Path $repoRoot ".test-localappdata-mongoose"

function Assert-True {
    param(
        [object]$Condition,
        [string]$Message
    )

    if (-not $Condition) {
        throw $Message
    }
}

function Invoke-Mongoose {
    param([string[]]$Arguments)

    $output = & python $mongooseCli @Arguments 2>&1
    return [pscustomobject]@{
        ExitCode = $LASTEXITCODE
        Output = ($output | Out-String)
    }
}

Assert-True (Test-Path $mongooseCli) "mongoose CLI is missing."

if (Test-Path $testLocalAppData) {
    Remove-Item -Path $testLocalAppData -Recurse -Force
}
New-Item -ItemType Directory -Path $testLocalAppData -Force | Out-Null
$env:LOCALAPPDATA = $testLocalAppData

$setup = Invoke-Mongoose -Arguments @("setup", "--registry-root", $repoRoot)
Assert-True ($setup.ExitCode -eq 0) "mongoose setup failed. Output: $($setup.Output)"

$help = Invoke-Mongoose -Arguments @("--help")
Assert-True ($help.ExitCode -eq 0) "mongoose --help failed. Output: $($help.Output)"
Assert-True ($help.Output -match "mongoose install Njord") "mongoose --help did not include install example."
Assert-True ($help.Output -match "mongoose update") "mongoose --help did not include update guidance."
Assert-True ($help.Output -match "mongoose state --init") "mongoose --help did not include state guidance."

$state = Invoke-Mongoose -Arguments @("state", "--init", "--json")
Assert-True ($state.ExitCode -eq 0) "mongoose state failed. Output: $($state.Output)"
$statePaths = $state.Output | ConvertFrom-Json
Assert-True (Test-Path $statePaths.state) "mongoose state did not create the shared state directory."
Assert-True (Test-Path $statePaths.logs) "mongoose state did not create the log directory."
Assert-True (Test-Path $statePaths.jobs) "mongoose state did not create the jobs directory."

$list = Invoke-Mongoose -Arguments @("list")
Assert-True ($list.ExitCode -eq 0) "mongoose list failed. Output: $($list.Output)"
Assert-True ($list.Output -match "Njord") "mongoose list did not include Njord."

$missing = Invoke-Mongoose -Arguments @("install", "DefinitelyMissingAgent")
Assert-True ($missing.ExitCode -ne 0) "mongoose install unexpectedly succeeded for a missing agent."
Assert-True ($missing.Output -match "does not exist") "missing-agent output did not explain the failure."
Assert-True ($missing.Output -match "Available agents") "missing-agent output did not list available agents."

$install = Invoke-Mongoose -Arguments @("install", "Njord")
Assert-True ($install.ExitCode -eq 0) "mongoose install Njord failed. Output: $($install.Output)"

$launcherPath = Join-Path $testLocalAppData "Agents\bin\Njord.cmd"
Assert-True (Test-Path $launcherPath) "mongoose did not create Njord launcher."

$launcher = Get-Content -Raw -Path $launcherPath
Assert-True ($launcher -match "\sask\s") "Njord launcher does not call ask."
Assert-True ($launcher -match "njord") "Njord launcher does not point at Njord."

$uninstall = Invoke-Mongoose -Arguments @("uninstall", "Njord")
Assert-True ($uninstall.ExitCode -eq 0) "mongoose uninstall Njord failed. Output: $($uninstall.Output)"
Assert-True (-not (Test-Path $launcherPath)) "mongoose uninstall did not remove Njord launcher."

Write-Host "Mongoose validation passed."

