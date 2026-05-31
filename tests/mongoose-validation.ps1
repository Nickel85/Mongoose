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
$fixtureRoot = Join-Path $repoRoot ".test-mongoose-fixtures"

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

function New-FixtureAgent {
    param(
        [string]$Name,
        [string]$Description
    )

    $agentDirectory = Join-Path $fixtureRoot "agents\$($Name.ToLowerInvariant())"
    New-Item -ItemType Directory -Path $agentDirectory -Force | Out-Null

    $agentPython = @"
import sys

print("$Name fixture agent")
print("ARGS=" + "|".join(sys.argv[1:]))
"@
    Set-Content -Path (Join-Path $agentDirectory "agent.py") -Value $agentPython -Encoding ASCII

    $manifest = @{
        commandName = $Name
        displayName = $Name
        version = "1.0.0"
        entrypointPath = "agent.py"
        example = "hello from $Name"
        description = $Description
        capabilities = @(
            @{
                name = "echo"
                description = "Echo fixture arguments."
                taskTypes = @("test", "echo")
                entrypointPath = "agent.py"
            }
        )
    } | ConvertTo-Json -Depth 5
    Set-Content -Path (Join-Path $agentDirectory "agent.json") -Value $manifest -Encoding ASCII

    return $agentDirectory
}

Assert-True (Test-Path $mongooseCli) "mongoose CLI is missing."

if (Test-Path $testLocalAppData) {
    Remove-Item -Path $testLocalAppData -Recurse -Force
}
if (Test-Path $fixtureRoot) {
    Remove-Item -Path $fixtureRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $testLocalAppData -Force | Out-Null
$alphaPath = New-FixtureAgent -Name "Alpha" -Description "Alpha fixture agent."
$betaPath = New-FixtureAgent -Name "Beta" -Description "Beta fixture agent."
$env:LOCALAPPDATA = $testLocalAppData

$setup = Invoke-Mongoose -Arguments @("setup", "--registry-root", $repoRoot)
Assert-True ($setup.ExitCode -eq 0) "mongoose setup failed. Output: $($setup.Output)"

$help = Invoke-Mongoose -Arguments @("--help")
Assert-True ($help.ExitCode -eq 0) "mongoose --help failed. Output: $($help.Output)"
Assert-True ($help.Output -match "mongoose install Njord") "mongoose --help did not include install example."
Assert-True ($help.Output -match "mongoose show Njord") "mongoose --help did not include show example."
Assert-True ($help.Output -match "mongoose run Njord") "mongoose --help did not include run example."
Assert-True ($help.Output -match "mongoose remove Njord") "mongoose --help did not include remove example."
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
Assert-True ($install.Output -match "State:") "mongoose install did not report installed state path."

$launcherPath = Join-Path $testLocalAppData "Agents\bin\Njord.cmd"
Assert-True (Test-Path $launcherPath) "mongoose did not create Njord launcher."
$njordStatePath = Join-Path $testLocalAppData "Agents\state\agents\Njord.json"
Assert-True (Test-Path $njordStatePath) "mongoose did not write Njord installed state."

$launcher = Get-Content -Raw -Path $launcherPath
Assert-True ($launcher -match "\sask\s") "Njord launcher does not call ask."
Assert-True ($launcher -match "njord") "Njord launcher does not point at Njord."

$showNjord = Invoke-Mongoose -Arguments @("show", "Njord")
Assert-True ($showNjord.ExitCode -eq 0) "mongoose show Njord failed. Output: $($showNjord.Output)"
Assert-True ($showNjord.Output -match "Status: installed") "mongoose show Njord did not report installed status."
Assert-True ($showNjord.Output -match "Capabilities") "mongoose show Njord did not include capabilities."

$installedList = Invoke-Mongoose -Arguments @("list", "--installed")
Assert-True ($installedList.ExitCode -eq 0) "mongoose list --installed failed. Output: $($installedList.Output)"
Assert-True ($installedList.Output -match "Njord") "mongoose list --installed did not include Njord."

$uninstall = Invoke-Mongoose -Arguments @("uninstall", "Njord")
Assert-True ($uninstall.ExitCode -eq 0) "mongoose uninstall Njord failed. Output: $($uninstall.Output)"
Assert-True (-not (Test-Path $launcherPath)) "mongoose uninstall did not remove Njord launcher."
Assert-True (-not (Test-Path $njordStatePath)) "mongoose uninstall did not remove Njord installed state."

$setupFixtures = Invoke-Mongoose -Arguments @("setup", "--registry-root", $fixtureRoot)
Assert-True ($setupFixtures.ExitCode -eq 0) "mongoose setup for fixture registry failed. Output: $($setupFixtures.Output)"

$fixtureList = Invoke-Mongoose -Arguments @("list")
Assert-True ($fixtureList.ExitCode -eq 0) "mongoose list fixture registry failed. Output: $($fixtureList.Output)"
Assert-True ($fixtureList.Output -match "Alpha") "mongoose list did not include Alpha fixture."
Assert-True ($fixtureList.Output -match "Beta") "mongoose list did not include Beta fixture."

$installAlphaByPath = Invoke-Mongoose -Arguments @("install", $alphaPath)
Assert-True ($installAlphaByPath.ExitCode -eq 0) "mongoose install by path failed. Output: $($installAlphaByPath.Output)"
$alphaLauncher = Join-Path $testLocalAppData "Agents\bin\Alpha.cmd"
$alphaStatePath = Join-Path $testLocalAppData "Agents\state\agents\Alpha.json"
Assert-True (Test-Path $alphaLauncher) "mongoose install by path did not create Alpha launcher."
Assert-True (Test-Path $alphaStatePath) "mongoose install by path did not write Alpha state."

$showAlpha = Invoke-Mongoose -Arguments @("show", "Alpha")
Assert-True ($showAlpha.ExitCode -eq 0) "mongoose show Alpha failed. Output: $($showAlpha.Output)"
Assert-True ($showAlpha.Output -match "Version: 1.0.0") "mongoose show Alpha did not include version."
Assert-True ($showAlpha.Output -match "echo") "mongoose show Alpha did not include capability metadata."

$runAlpha = Invoke-Mongoose -Arguments @("run", "Alpha", "echo", "hello")
Assert-True ($runAlpha.ExitCode -eq 0) "mongoose run Alpha failed. Output: $($runAlpha.Output)"
Assert-True ($runAlpha.Output -match "Alpha fixture agent") "mongoose run Alpha did not execute fixture agent."
Assert-True ($runAlpha.Output -match "ARGS=echo\|hello") "mongoose run Alpha did not pass agent arguments."

$removeAlpha = Invoke-Mongoose -Arguments @("remove", "Alpha")
Assert-True ($removeAlpha.ExitCode -eq 0) "mongoose remove Alpha failed. Output: $($removeAlpha.Output)"
Assert-True (-not (Test-Path $alphaLauncher)) "mongoose remove did not remove Alpha launcher."
Assert-True (-not (Test-Path $alphaStatePath)) "mongoose remove did not remove Alpha state."

Write-Host "Mongoose validation passed."

