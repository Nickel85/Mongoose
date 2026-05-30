<#
.SYNOPSIS
Smoke-tests the built mongoose.exe package manager.
#>

[CmdletBinding()]
param(
    [string]$MongooseExe = ""
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $MongooseExe) {
    $MongooseExe = Join-Path $repoRoot "dist\mongoose.exe"
}

$MongooseExe = (Resolve-Path $MongooseExe).Path
$testLocalAppData = Join-Path $repoRoot ".test-localappdata-mongoose-exe"
$testCloneRoot = Join-Path $repoRoot ".test-mongoose-update-registry"

function Assert-True {
    param(
        [object]$Condition,
        [string]$Message
    )

    if (-not $Condition) {
        throw $Message
    }
}

function Invoke-MongooseExe {
    param([string[]]$Arguments)

    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $MongooseExe
    $quotedArguments = $Arguments | ForEach-Object {
        '"' + ($_ -replace '"', '\"') + '"'
    }
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

Assert-True (Test-Path $MongooseExe) "mongoose.exe is missing: $MongooseExe"

foreach ($path in @($testLocalAppData, $testCloneRoot)) {
    if (Test-Path $path) {
        Remove-Item -Path $path -Recurse -Force
    }
}

New-Item -ItemType Directory -Path $testLocalAppData -Force | Out-Null
$env:LOCALAPPDATA = $testLocalAppData

$setup = Invoke-MongooseExe -Arguments @("setup", "--registry-root", $repoRoot)
Assert-True ($setup.ExitCode -eq 0) "mongoose setup failed. Output: $($setup.Output)"

$state = Invoke-MongooseExe -Arguments @("state", "--init", "--json")
Assert-True ($state.ExitCode -eq 0) "mongoose state failed. Output: $($state.Output)"
$statePaths = $state.Output | ConvertFrom-Json
Assert-True (Test-Path $statePaths.state) "mongoose state did not create the shared state directory."
Assert-True (Test-Path $statePaths.logs) "mongoose state did not create the log directory."
Assert-True (Test-Path $statePaths.jobs) "mongoose state did not create the jobs directory."

$list = Invoke-MongooseExe -Arguments @("list")
Assert-True ($list.ExitCode -eq 0) "mongoose list failed. Output: $($list.Output)"
Assert-True ($list.Output -match "Midas") "mongoose list did not include Midas."

$install = Invoke-MongooseExe -Arguments @("install", "Midas")
Assert-True ($install.ExitCode -eq 0) "mongoose install Midas failed. Output: $($install.Output)"

$nickLauncher = Join-Path $testLocalAppData "Agents\bin\Midas.cmd"
Assert-True (Test-Path $nickLauncher) "mongoose install did not create Midas launcher."

$uninstall = Invoke-MongooseExe -Arguments @("uninstall", "Midas")
Assert-True ($uninstall.ExitCode -eq 0) "mongoose uninstall Midas failed. Output: $($uninstall.Output)"
Assert-True (-not (Test-Path $nickLauncher)) "mongoose uninstall did not remove Midas launcher."

$setupForUpdate = Invoke-MongooseExe -Arguments @(
    "setup",
    "--registry-root",
    $testCloneRoot,
    "--registry-url",
    $repoRoot
)
Assert-True ($setupForUpdate.ExitCode -eq 0) "mongoose setup for update failed. Output: $($setupForUpdate.Output)"

$update = Invoke-MongooseExe -Arguments @("update")
Assert-True ($update.ExitCode -eq 0) "mongoose update failed. Output: $($update.Output)"
Assert-True (Test-Path (Join-Path $testCloneRoot "agents\midas\agent.json")) "mongoose update did not clone the registry."

Write-Host "Mongoose EXE smoke tests passed."
