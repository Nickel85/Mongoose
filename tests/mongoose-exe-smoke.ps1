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

$list = Invoke-MongooseExe -Arguments @("list")
Assert-True ($list.ExitCode -eq 0) "mongoose list failed. Output: $($list.Output)"
Assert-True ($list.Output -match "Nick") "mongoose list did not include Nick."

$install = Invoke-MongooseExe -Arguments @("install", "Nick")
Assert-True ($install.ExitCode -eq 0) "mongoose install Nick failed. Output: $($install.Output)"

$nickLauncher = Join-Path $testLocalAppData "Agents\bin\Nick.cmd"
Assert-True (Test-Path $nickLauncher) "mongoose install did not create Nick launcher."

$uninstall = Invoke-MongooseExe -Arguments @("uninstall", "Nick")
Assert-True ($uninstall.ExitCode -eq 0) "mongoose uninstall Nick failed. Output: $($uninstall.Output)"
Assert-True (-not (Test-Path $nickLauncher)) "mongoose uninstall did not remove Nick launcher."

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
Assert-True (Test-Path (Join-Path $testCloneRoot "agents\personal-cfo\agent.json")) "mongoose update did not clone the registry."

Write-Host "Mongoose EXE smoke tests passed."
