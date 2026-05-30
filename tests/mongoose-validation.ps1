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
Assert-True ($help.Output -match "mongoose install Midas") "mongoose --help did not include install example."
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
Assert-True ($list.Output -match "Midas") "mongoose list did not include Midas."

$missing = Invoke-Mongoose -Arguments @("install", "DefinitelyMissingAgent")
Assert-True ($missing.ExitCode -ne 0) "mongoose install unexpectedly succeeded for a missing agent."
Assert-True ($missing.Output -match "does not exist") "missing-agent output did not explain the failure."
Assert-True ($missing.Output -match "Available agents") "missing-agent output did not list available agents."

$install = Invoke-Mongoose -Arguments @("install", "Midas")
Assert-True ($install.ExitCode -eq 0) "mongoose install Midas failed. Output: $($install.Output)"

$launcherPath = Join-Path $testLocalAppData "Agents\bin\Midas.cmd"
Assert-True (Test-Path $launcherPath) "mongoose did not create Midas launcher."

$launcher = Get-Content -Raw -Path $launcherPath
Assert-True ($launcher -match "\sask\s") "Midas launcher does not call ask."
Assert-True ($launcher -match "midas") "Midas launcher does not point at Midas."

$uninstall = Invoke-Mongoose -Arguments @("uninstall", "Midas")
Assert-True ($uninstall.ExitCode -eq 0) "mongoose uninstall Midas failed. Output: $($uninstall.Output)"
Assert-True (-not (Test-Path $launcherPath)) "mongoose uninstall did not remove Midas launcher."

Write-Host "Mongoose validation passed."
