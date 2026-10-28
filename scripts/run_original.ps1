param(
    [string]$Plan = 'reproduction/plans/probe.json',
    [string]$LicenseFile = '',
    [string]$Log = 'tmp/reproduction/original.log'
)
$ErrorActionPreference = 'Stop'
$referenceRoot = Split-Path -Parent $PSScriptRoot
$referenceJulia = Join-Path $referenceRoot '.tools\julia-1.9.2\bin\julia.exe'
if (-not (Test-Path -LiteralPath $referenceJulia)) {
    throw 'The project-local Julia runtime is missing. See reproduction/README.md.'
}
if ($LicenseFile) {
    $env:GRB_LICENSE_FILE = (Resolve-Path -LiteralPath $LicenseFile).Path
} elseif (-not $env:GRB_LICENSE_FILE) {
    $referenceTrial = Join-Path $referenceRoot '.venv\Lib\site-packages\gurobipy\gurobi.lic'
    if (Test-Path -LiteralPath $referenceTrial) { $env:GRB_LICENSE_FILE = $referenceTrial }
}
$env:JULIA_DEPOT_PATH = Join-Path $referenceRoot '.tools\julia-depot'
$env:JULIA_NUM_PRECOMPILE_TASKS = '2'
$referenceLog = Join-Path $referenceRoot $Log
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $referenceLog) | Out-Null
Push-Location $referenceRoot
try {
    # Windows PowerShell treats redirected native stderr as ErrorRecord objects.
    # Julia warnings must not abort an otherwise successful process.
    $ErrorActionPreference = 'Continue'
    & $referenceJulia --project=reproduction/docker_reference scripts/original_reference_runner.jl $Plan *> $referenceLog
    $referenceExitCode = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    exit $referenceExitCode
} finally {
    Pop-Location
}
