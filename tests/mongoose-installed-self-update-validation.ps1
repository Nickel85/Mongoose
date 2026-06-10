<#
.SYNOPSIS
Validates installed mongoose.exe self-update behavior without live network access.
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
$testLocalAppData = Join-Path $repoRoot ".test-localappdata-mongoose-installed-self-update"
$fixtureRoot = Join-Path $repoRoot ".test-mongoose-self-update-fixtures"
$installedExe = Join-Path $testLocalAppData "Agents\bin\mongoose.exe"
$appRoot = Join-Path $testLocalAppData "Agents\mongoose"
[byte[]]$script:marker = [Text.Encoding]::ASCII.GetBytes("MONGOOSE-INSTALLED-SELF-UPDATE-MARKER")

function Assert-True {
    param(
        [object]$Condition,
        [string]$Message
    )

    if (-not $Condition) {
        throw $Message
    }
}

function Invoke-InstalledMongoose {
    param(
        [string[]]$Arguments,
        [hashtable]$Environment = @{}
    )

    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $installedExe
    $quotedArguments = $Arguments | ForEach-Object {
        '"' + ($_ -replace '"', '\"') + '"'
    }
    $startInfo.Arguments = $quotedArguments -join " "
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.UseShellExecute = $false

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $startInfo
    $previousEnvironment = @{}
    foreach ($key in $Environment.Keys) {
        $previousEnvironment[$key] = [Environment]::GetEnvironmentVariable($key, "Process")
        [Environment]::SetEnvironmentVariable($key, [string]$Environment[$key], "Process")
    }

    try {
        [void]$process.Start()
        $stdout = $process.StandardOutput.ReadToEnd()
        $stderr = $process.StandardError.ReadToEnd()
        $process.WaitForExit()
    } finally {
        foreach ($key in $Environment.Keys) {
            [Environment]::SetEnvironmentVariable($key, $previousEnvironment[$key], "Process")
        }
    }

    return [pscustomobject]@{
        ExitCode = $process.ExitCode
        Output = ($stdout + $stderr)
    }
}

function New-ReleaseFixture {
    param(
        [string]$AssetPath
    )

    $assetUri = ([System.Uri](Resolve-Path $AssetPath).Path).AbsoluteUri
    $releases = @(
        @{
            tag_name = "v0.5.1"
            draft = $false
            prerelease = $false
            assets = @(
                @{
                    name = "mongoose.exe"
                    browser_download_url = $assetUri
                }
            )
        }
    )
    $release = ConvertTo-Json -InputObject $releases -Depth 6
    $releasePath = Join-Path $fixtureRoot "releases.json"
    Set-Content -Path $releasePath -Value $release -Encoding ASCII
    return ([System.Uri](Resolve-Path $releasePath).Path).AbsoluteUri
}

function Install-TestMongoose {
    New-Item -ItemType Directory -Path (Split-Path $installedExe -Parent) -Force | Out-Null
    Copy-Item -Path $MongooseExe -Destination $installedExe -Force
}

function Test-FileContainsMarker {
    param([string]$Path)

    $bytes = [IO.File]::ReadAllBytes($Path)
    if ($bytes.Length -lt $script:marker.Length) {
        return $false
    }

    for ($index = 0; $index -le $bytes.Length - $script:marker.Length; $index++) {
        $matched = $true
        for ($offset = 0; $offset -lt $script:marker.Length; $offset++) {
            if ($bytes[$index + $offset] -ne $script:marker[$offset]) {
                $matched = $false
                break
            }
        }
        if ($matched) {
            return $true
        }
    }
    return $false
}

function Wait-ForInstalledMarker {
    $deadline = (Get-Date).AddSeconds(20)
    while ((Get-Date) -lt $deadline) {
        if ((Test-Path $installedExe) -and (Test-FileContainsMarker -Path $installedExe)) {
            return
        }
        Start-Sleep -Milliseconds 250
    }
    throw "installed mongoose.exe was not replaced with the staged release asset."
}

foreach ($path in @($testLocalAppData, $fixtureRoot)) {
    if (Test-Path $path) {
        Remove-Item -Path $path -Recurse -Force
    }
}

New-Item -ItemType Directory -Path $testLocalAppData -Force | Out-Null
New-Item -ItemType Directory -Path $fixtureRoot -Force | Out-Null
$env:LOCALAPPDATA = $testLocalAppData

$releaseAsset = Join-Path $fixtureRoot "mongoose.exe"
Copy-Item -Path $MongooseExe -Destination $releaseAsset -Force
[IO.File]::WriteAllBytes($releaseAsset, [byte[]]([IO.File]::ReadAllBytes($releaseAsset) + $script:marker))
$releaseUrl = New-ReleaseFixture -AssetPath $releaseAsset

Install-TestMongoose
$version = Invoke-InstalledMongoose -Arguments @("--version")
Assert-True ($version.ExitCode -eq 0) "installed mongoose.exe --version failed. Output: $($version.Output)"
Assert-True ($version.Output -match "mongoose 0.5.0") "installed mongoose.exe did not report expected version. Output: $($version.Output)"

$update = Invoke-InstalledMongoose -Arguments @("update", "--self") -Environment @{
    MONGOOSE_RELEASES_API_URL = $releaseUrl
}
Assert-True ($update.ExitCode -eq 0) "installed mongoose.exe self-update failed. Output: $($update.Output)"
Assert-True ($update.Output -match "Downloaded Mongoose 0.5.1; replacement will finish after this command exits.") "self-update did not report deferred replacement. Output: $($update.Output)"
Assert-True (Test-Path (Join-Path $appRoot "apply-mongoose-update.ps1")) "self-update did not write the deferred replacement script."
Wait-ForInstalledMarker

Install-TestMongoose
Get-ChildItem -Path $appRoot -Filter ".mongoose.exe.*.download" -ErrorAction SilentlyContinue | Remove-Item -Force
$failedUpdate = Invoke-InstalledMongoose -Arguments @("update", "--self") -Environment @{
    MONGOOSE_RELEASES_API_URL = $releaseUrl
    MONGOOSE_DISABLE_DEFERRED_SELF_UPDATE = "1"
}
Assert-True ($failedUpdate.ExitCode -ne 0) "self-update unexpectedly succeeded when deferred replacement was disabled. Output: $($failedUpdate.Output)"
Assert-True ($failedUpdate.Output -match "Downloaded update to") "failed replacement output did not include the staged recovery path. Output: $($failedUpdate.Output)"
Assert-True ($failedUpdate.Output -match "could not replace") "failed replacement output did not explain the target replacement failure. Output: $($failedUpdate.Output)"
Assert-True ($failedUpdate.Output -match "Retry later, or download mongoose.exe manually") "failed replacement output did not include manual recovery guidance. Output: $($failedUpdate.Output)"
$stagedDownloads = @(Get-ChildItem -Path $appRoot -Filter ".mongoose.exe.v0.5.1.*.download")
Assert-True ($stagedDownloads.Count -ge 1) "failed replacement did not leave a staged download for recovery."

Write-Host "Installed mongoose.exe self-update validation passed."
