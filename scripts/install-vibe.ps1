# install-vibe.ps1 — install a global `vibe` command for the current user.
#
# Creates %USERPROFILE%\bin\vibe.cmd that forwards to this repo's scripts\vibe.ps1,
# and adds %USERPROFILE%\bin to the User PATH (asks first unless --yes).
#
# Flags (accepts both --flag and -Flag forms):
#   --dry-run   show what would happen; make no changes
#   --yes       don't prompt before modifying PATH
#
# Does not require admin. Never prints secrets.

$ErrorActionPreference = 'Stop'

$DryRun = ($args -contains '--dry-run') -or ($args -contains '-DryRun')
$Yes    = ($args -contains '--yes')     -or ($args -contains '-Yes')

# Repo root = parent of this scripts directory (or VIBE_COUNCIL_HOME override).
$repo = if ($env:VIBE_COUNCIL_HOME) { $env:VIBE_COUNCIL_HOME } else { Split-Path -Parent $PSScriptRoot }
$ps1  = Join-Path $repo 'scripts\vibe.ps1'

$bin  = Join-Path $env:USERPROFILE 'bin'
$shim = Join-Path $bin 'vibe.cmd'

$shimContent = @"
@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "$ps1" %*
exit /b %ERRORLEVEL%
"@

Write-Host "vibe-council repo : $repo"
Write-Host "Launcher script   : $ps1"
Write-Host "Shim to create    : $shim"
Write-Host "PATH dir          : $bin"

if (-not (Test-Path $ps1)) {
    Write-Error "Launcher not found: $ps1"
    exit 1
}

$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
$onPath = $userPath -and ($userPath.Split(';') -contains $bin)

if ($DryRun) {
    Write-Host ""
    Write-Host "[dry-run] Would create directory : $bin"
    Write-Host "[dry-run] Would write shim       : $shim"
    if ($onPath) { Write-Host "[dry-run] PATH already contains  : $bin" }
    else { Write-Host "[dry-run] Would add to User PATH : $bin" }
    Write-Host "[dry-run] No changes made."
    exit 0
}

# Create bin and shim.
if (-not (Test-Path $bin)) { New-Item -ItemType Directory -Path $bin | Out-Null }
Set-Content -Path $shim -Value $shimContent -Encoding ASCII
Write-Host "Wrote shim: $shim"

# Update PATH if needed.
if ($onPath) {
    Write-Host "$bin already on User PATH."
} else {
    $doIt = $Yes
    if (-not $doIt) {
        if ([Environment]::UserInteractive) {
            $resp = Read-Host "Add '$bin' to your User PATH? [Y/n]"
            $doIt = ($resp -eq '') -or ($resp -match '^(y|yes)$')
        } else {
            Write-Host "Non-interactive: re-run with --yes to update PATH. Skipped."
        }
    }
    if ($doIt) {
        $newPath = if ($userPath) { "$userPath;$bin" } else { $bin }
        [Environment]::SetEnvironmentVariable('Path', $newPath, 'User')
        Write-Host "Added '$bin' to User PATH. Restart your shell to pick it up."
    } else {
        Write-Host "Skipped PATH update. Add '$bin' to PATH manually to use 'vibe' globally."
    }
}

Write-Host ""
Write-Host "Done. Try:  vibe help"
