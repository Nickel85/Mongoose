<#
.SYNOPSIS
Validates the mongoose capability runtime CLI behavior without requiring a compiler.
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

    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = "python"
    $quotedArguments = @('"' + ($mongooseCli -replace '"', '\"') + '"') + ($Arguments | ForEach-Object {
        '"' + ($_ -replace '"', '\"') + '"'
    })
    $startInfo.Arguments = $quotedArguments -join " "
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.UseShellExecute = $false

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $startInfo
    [void]$process.Start()
    $stdout = $process.StandardOutput.ReadToEnd()
    $stderr = $process.StandardError.ReadToEnd()
    $process.WaitForExit()

    return [pscustomobject]@{
        ExitCode = $process.ExitCode
        Output = ($stdout + $stderr)
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

    $capabilities = @(
        @{
            name = "echo"
            description = "Echo fixture arguments."
            taskTypes = @("test", "echo")
            entrypointPath = "agent.py"
        }
    )
    if ($Name -eq "Alpha") {
        $capabilities += @{
            name = "plan"
            description = "Plan fixture work."
            taskTypes = @("planning", "work-plan")
            entrypointPath = "agent.py"
        }
    }
    if ($Name -eq "Beta") {
        $capabilities += @{
            name = "report"
            description = "Build fixture reports and summaries."
            taskTypes = @("report", "summary")
            entrypointPath = "agent.py"
        }
    }

    $manifest = @{
        commandName = $Name
        displayName = $Name
        version = "1.0.0"
        entrypointPath = "agent.py"
        example = "hello from $Name"
        description = $Description
        capabilities = $capabilities
    } | ConvertTo-Json -Depth 5
    Set-Content -Path (Join-Path $agentDirectory "agent.json") -Value $manifest -Encoding ASCII

    return $agentDirectory
}

function New-InvalidFixtureAgent {
    $agentDirectory = Join-Path $fixtureRoot "agents\invalid"
    New-Item -ItemType Directory -Path $agentDirectory -Force | Out-Null
    Set-Content -Path (Join-Path $agentDirectory "agent.py") -Value "print('invalid')" -Encoding ASCII
    $manifest = @{
        commandName = "Invalid"
        displayName = "Invalid"
        entrypointPath = "missing.py"
        example = "invalid"
        description = "Invalid fixture."
        capabilities = @(
            @{
                name = "broken"
                description = "Broken fixture."
                taskTypes = "not-a-list"
            }
        )
    } | ConvertTo-Json -Depth 5
    Set-Content -Path (Join-Path $agentDirectory "agent.json") -Value $manifest -Encoding ASCII
    return $agentDirectory
}

function New-UnsupportedSchemaFixtureAgent {
    $agentDirectory = Join-Path $fixtureRoot "agents\unsupported-schema"
    New-Item -ItemType Directory -Path $agentDirectory -Force | Out-Null
    Set-Content -Path (Join-Path $agentDirectory "agent.py") -Value "print('unsupported schema')" -Encoding ASCII
    $manifest = @{
        schemaVersion = 999
        commandName = "UnsupportedSchema"
        displayName = "Unsupported Schema"
        entrypointPath = "agent.py"
        example = "unsupported"
        description = "Fixture with a manifest schema newer than this Mongoose supports."
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
$invalidPath = New-InvalidFixtureAgent
$env:LOCALAPPDATA = $testLocalAppData

$setup = Invoke-Mongoose -Arguments @("setup", "--registry-root", $repoRoot)
Assert-True ($setup.ExitCode -eq 0) "mongoose setup failed. Output: $($setup.Output)"

$help = Invoke-Mongoose -Arguments @("--help")
Assert-True ($help.ExitCode -eq 0) "mongoose --help failed. Output: $($help.Output)"
Assert-True ($help.Output -match "mongoose --version") "mongoose --help did not include version example."
Assert-True ($help.Output -match "mongoose capabilities") "mongoose --help did not include capabilities example."
Assert-True ($help.Output -match "mongoose install Njord") "mongoose --help did not include install example."
Assert-True ($help.Output -match "mongoose show Njord") "mongoose --help did not include show example."
Assert-True ($help.Output -match "mongoose run Njord") "mongoose --help did not include run example."
Assert-True ($help.Output -match "mongoose route") "mongoose --help did not include route example."
Assert-True ($help.Output -match "mongoose validate") "mongoose --help did not include validate example."
Assert-True ($help.Output -match "mongoose remove Njord") "mongoose --help did not include remove example."
Assert-True ($help.Output -match "mongoose update") "mongoose --help did not include update guidance."
Assert-True ($help.Output -match "mongoose state --init") "mongoose --help did not include state guidance."

$version = Invoke-Mongoose -Arguments @("--version")
Assert-True ($version.ExitCode -eq 0) "mongoose --version failed. Output: $($version.Output)"
Assert-True ($version.Output -match "mongoose 0.2.0") "mongoose --version did not report expected version."
Assert-True ($version.Output -match "development") "mongoose --version did not report development release kind."

$state = Invoke-Mongoose -Arguments @("state", "--init", "--json")
Assert-True ($state.ExitCode -eq 0) "mongoose state failed. Output: $($state.Output)"
$statePaths = $state.Output | ConvertFrom-Json
Assert-True (Test-Path $statePaths.state) "mongoose state did not create the shared state directory."
Assert-True (Test-Path $statePaths.logs) "mongoose state did not create the log directory."
Assert-True (Test-Path $statePaths.jobs) "mongoose state did not create the jobs directory."
Assert-True ($statePaths.version -eq "0.2.0") "mongoose state did not report CLI version."
Assert-True ($statePaths.releaseKind -eq "development") "mongoose state did not report development release kind."
Assert-True ($statePaths.releaseTag -eq "") "mongoose state should not report a release tag for development builds."
Assert-True ($statePaths.cliSource -match "mongoose.py") "mongoose state did not report CLI source."
Assert-True ($statePaths.registry -eq $repoRoot) "mongoose state did not report configured registry path."
Assert-True ($statePaths.registryRevision -notin @("", "missing", "not a git checkout")) "mongoose state did not report registry Git revision."
Assert-True ($statePaths.registryStatus -in @("clean", "dirty")) "mongoose state did not report registry Git status."

$list = Invoke-Mongoose -Arguments @("list")
Assert-True ($list.ExitCode -eq 0) "mongoose list failed. Output: $($list.Output)"
Assert-True ($list.Output -match "Njord") "mongoose list did not include Njord."

$validateRegistry = Invoke-Mongoose -Arguments @("validate")
Assert-True ($validateRegistry.ExitCode -eq 0) "mongoose validate failed. Output: $($validateRegistry.Output)"
Assert-True ($validateRegistry.Output -match "Validated") "mongoose validate did not report validated manifests."

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
Assert-True ($showNjord.Output -match "Manifest schema: 1") "mongoose show Njord did not include manifest schema."
Assert-True ($showNjord.Output -match "Task types: finance") "mongoose show Njord did not include task types."
Assert-True ($showNjord.Output -match "Required config: YNAB_ACCESS_TOKEN") "mongoose show Njord did not include configuration requirements."
Assert-True ($showNjord.Output -match "LLM mode: none") "mongoose show Njord did not include LLM metadata."

$installedList = Invoke-Mongoose -Arguments @("list", "--installed")
Assert-True ($installedList.ExitCode -eq 0) "mongoose list --installed failed. Output: $($installedList.Output)"
Assert-True ($installedList.Output -match "Njord") "mongoose list --installed did not include Njord."

$uninstall = Invoke-Mongoose -Arguments @("uninstall", "Njord")
Assert-True ($uninstall.ExitCode -eq 0) "mongoose uninstall Njord failed. Output: $($uninstall.Output)"
Assert-True (-not (Test-Path $launcherPath)) "mongoose uninstall did not remove Njord launcher."
Assert-True (-not (Test-Path $njordStatePath)) "mongoose uninstall did not remove Njord installed state."

$validateInvalid = Invoke-Mongoose -Arguments @("validate", $invalidPath)
Assert-True ($validateInvalid.ExitCode -ne 0) "mongoose validate unexpectedly passed invalid fixture. Output: $($validateInvalid.Output)"
Assert-True ($validateInvalid.Output -match "Invalid agent manifest") "invalid manifest output did not identify the manifest."
Assert-True ($validateInvalid.Output -match "entrypointPath does not exist") "invalid manifest output did not explain the missing entrypoint."
Assert-True ($validateInvalid.Output -match "taskTypes must be a list") "invalid manifest output did not explain invalid capability taskTypes."

Remove-Item -Path $invalidPath -Recurse -Force

$unsupportedSchemaPath = New-UnsupportedSchemaFixtureAgent
$validateUnsupportedSchema = Invoke-Mongoose -Arguments @("validate", $unsupportedSchemaPath)
Assert-True ($validateUnsupportedSchema.ExitCode -ne 0) "mongoose validate unexpectedly passed unsupported schema fixture. Output: $($validateUnsupportedSchema.Output)"
Assert-True ($validateUnsupportedSchema.Output -match "schemaVersion 999 is newer than supported version 1") "unsupported schema output did not explain the compatibility failure."

Remove-Item -Path $unsupportedSchemaPath -Recurse -Force

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

$installBetaByPath = Invoke-Mongoose -Arguments @("install", $betaPath)
Assert-True ($installBetaByPath.ExitCode -eq 0) "mongoose install by path for Beta failed. Output: $($installBetaByPath.Output)"
$betaLauncher = Join-Path $testLocalAppData "Agents\bin\Beta.cmd"
$betaStatePath = Join-Path $testLocalAppData "Agents\state\agents\Beta.json"
Assert-True (Test-Path $betaLauncher) "mongoose install by path did not create Beta launcher."
Assert-True (Test-Path $betaStatePath) "mongoose install by path did not write Beta state."

$showAlpha = Invoke-Mongoose -Arguments @("show", "Alpha")
Assert-True ($showAlpha.ExitCode -eq 0) "mongoose show Alpha failed. Output: $($showAlpha.Output)"
Assert-True ($showAlpha.Output -match "Version: 1.0.0") "mongoose show Alpha did not include version."
Assert-True ($showAlpha.Output -match "echo") "mongoose show Alpha did not include capability metadata."

$capabilities = Invoke-Mongoose -Arguments @("capabilities")
Assert-True ($capabilities.ExitCode -eq 0) "mongoose capabilities failed. Output: $($capabilities.Output)"
Assert-True ($capabilities.Output -match "Alpha::echo") "mongoose capabilities did not include Alpha echo."
Assert-True ($capabilities.Output -match "Alpha::plan") "mongoose capabilities did not include Alpha plan."
Assert-True ($capabilities.Output -match "Beta::report") "mongoose capabilities did not include Beta report."

$routeAlpha = Invoke-Mongoose -Arguments @("route", "--task-type", "work-plan", "build", "steps")
Assert-True ($routeAlpha.ExitCode -eq 0) "mongoose route did not dispatch to Alpha. Output: $($routeAlpha.Output)"
Assert-True ($routeAlpha.Output -match "Selected: Alpha::plan") "mongoose route did not select Alpha plan."
Assert-True ($routeAlpha.Output -match "Alpha fixture agent") "mongoose route did not execute Alpha fixture."
Assert-True ($routeAlpha.Output -match "ARGS=plan\|build\|steps") "mongoose route did not pass Alpha capability arguments."

$routeBeta = Invoke-Mongoose -Arguments @("route", "please", "build", "a", "summary")
Assert-True ($routeBeta.ExitCode -eq 0) "mongoose route did not dispatch to Beta from natural-language request. Output: $($routeBeta.Output)"
Assert-True ($routeBeta.Output -match "Selected: Beta::report") "mongoose route did not select Beta report."
Assert-True ($routeBeta.Output -match "Beta fixture agent") "mongoose route did not execute Beta fixture."
Assert-True ($routeBeta.Output -match "ARGS=report\|please\|build\|a\|summary") "mongoose route did not pass Beta capability arguments."

$ambiguousRoute = Invoke-Mongoose -Arguments @("route", "--task-type", "test", "--dry-run")
Assert-True ($ambiguousRoute.ExitCode -ne 0) "mongoose route unexpectedly resolved an ambiguous task type. Output: $($ambiguousRoute.Output)"
Assert-True ($ambiguousRoute.Output -match "Ambiguous request") "ambiguous route output did not explain ambiguity."
Assert-True ($ambiguousRoute.Output -match "Alpha::echo") "ambiguous route output did not include Alpha echo."
Assert-True ($ambiguousRoute.Output -match "Beta::echo") "ambiguous route output did not include Beta echo."

$missingRoute = Invoke-Mongoose -Arguments @("route", "--task-type", "definitely-missing")
Assert-True ($missingRoute.ExitCode -ne 0) "mongoose route unexpectedly resolved unsupported task type. Output: $($missingRoute.Output)"
Assert-True ($missingRoute.Output -match "No installed capability can handle") "unsupported route output did not explain the failure."

$runAlpha = Invoke-Mongoose -Arguments @("run", "Alpha", "echo", "hello")
Assert-True ($runAlpha.ExitCode -eq 0) "mongoose run Alpha failed. Output: $($runAlpha.Output)"
Assert-True ($runAlpha.Output -match "Alpha fixture agent") "mongoose run Alpha did not execute fixture agent."
Assert-True ($runAlpha.Output -match "ARGS=echo\|hello") "mongoose run Alpha did not pass agent arguments."

$removeAlpha = Invoke-Mongoose -Arguments @("remove", "Alpha")
Assert-True ($removeAlpha.ExitCode -eq 0) "mongoose remove Alpha failed. Output: $($removeAlpha.Output)"
Assert-True (-not (Test-Path $alphaLauncher)) "mongoose remove did not remove Alpha launcher."
Assert-True (-not (Test-Path $alphaStatePath)) "mongoose remove did not remove Alpha state."

$removeBeta = Invoke-Mongoose -Arguments @("remove", "Beta")
Assert-True ($removeBeta.ExitCode -eq 0) "mongoose remove Beta failed. Output: $($removeBeta.Output)"
Assert-True (-not (Test-Path $betaLauncher)) "mongoose remove did not remove Beta launcher."
Assert-True (-not (Test-Path $betaStatePath)) "mongoose remove did not remove Beta state."

Write-Host "Mongoose validation passed."

