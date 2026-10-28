param(
    [string]$Plan = 'reproduction/plans/model_checks.json',
    [string]$Log = 'tmp/reproduction/model_exchange.log'
)
$ErrorActionPreference = 'Stop'
$referenceRoot = Split-Path -Parent $PSScriptRoot
$referenceJulia = Join-Path $referenceRoot '.tools\julia-1.9.2\bin\julia.exe'
if (-not (Test-Path -LiteralPath $referenceJulia)) { throw 'See reproduction/README.md to prepare Julia.' }
$env:JULIA_DEPOT_PATH = Join-Path $referenceRoot '.tools\julia-depot'
$env:JULIA_NUM_PRECOMPILE_TASKS = '2'
$referenceLog = Join-Path $referenceRoot $Log
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $referenceLog) | Out-Null
Push-Location $referenceRoot
try {
    # Allow ordinary Julia stderr warnings; use its actual process exit code.
    $ErrorActionPreference = 'Continue'
    & $referenceJulia --project=reproduction/docker_reference scripts/original_model_exchange.jl $Plan *> $referenceLog
    $referenceExitCode = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    exit $referenceExitCode
} finally {
    Pop-Location
}
