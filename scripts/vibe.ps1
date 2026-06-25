# vibe.ps1 — global launcher for the vibe-council CLI.
#
# Runs `python -m backend.cli` inside the vibe-council repo while remembering the
# caller's working directory (exposed to the CLI via VIBE_CALLER_CWD) so that
# project-local .council/ artifacts are written in the caller's project.
#
# Repo location: $env:VIBE_COUNCIL_HOME if set, else the default below.
# Never prints the API key.

$ErrorActionPreference = 'Stop'

$repo = if ($env:VIBE_COUNCIL_HOME) { $env:VIBE_COUNCIL_HOME } else { 'C:\Users\F\Desktop\llm-council' }

if (-not (Test-Path $repo)) {
    Write-Error "vibe-council repo not found: $repo. Set VIBE_COUNCIL_HOME."
    exit 1
}

# Remember where the user invoked vibe from; the CLI reads this.
$callerCwd = (Get-Location).Path
$env:VIBE_CALLER_CWD = $callerCwd

# Prefer the repo's venv Python; fall back to whatever `python` is on PATH.
$py = Join-Path $repo '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) { $py = 'python' }

Push-Location $repo
try {
    & $py -m backend.cli @args
    $code = $LASTEXITCODE
}
finally {
    Pop-Location
    Remove-Item Env:\VIBE_CALLER_CWD -ErrorAction SilentlyContinue
}

exit $code
