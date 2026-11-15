<#
.SYNOPSIS
  Set up pios-algo on a Windows machine, or check an existing setup.
.DESCRIPTION
  Installs or updates to the latest: uv and the Visual Studio C++ Build Tools.
  Python comes from .python-version (latest patch); packages resolve from pyproject.toml.
  The build downloads CMake and Ninja itself (scikit-build-core).
.PARAMETER Check
  Report what is missing; install nothing. The VS Code folder-open task uses this.
.PARAMETER Upgrade
  Also upgrade installed packages to the newest versions pyproject.toml allows.
#>
[CmdletBinding()]
param(
    [switch]$Check,
    [switch]$Upgrade,
    [string]$BuildToolsId = 'Microsoft.VisualStudio.2022.BuildTools'
)

$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
$missing = @()

function Step([string]$msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Have([string]$cmd) { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }

# 1. uv
Step 'uv'
if (Have 'uv') {
    if (-not $Check) {
        uv self update
        if ($LASTEXITCODE -ne 0) { Write-Warning 'uv self update skipped (uv was not installed by the standalone installer)' }
    }
} elseif ($Check) {
    $missing += 'uv'
} else {
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}

# 2. C++ Build Tools (MSVC)
Step 'C++ Build Tools'
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
$vc = $null
if (Test-Path $vswhere) {
    $vc = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
}
if ($vc) {
    Write-Host "found: $vc"
    if (-not $Check -and (Have 'winget')) {
        winget upgrade --id $BuildToolsId -e --accept-package-agreements --accept-source-agreements
    }
} elseif ($Check) {
    $missing += 'C++ Build Tools'
} elseif (Have 'winget') {
    winget install --id $BuildToolsId -e --accept-package-agreements --accept-source-agreements `
        --override '--quiet --wait --norestart --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended'
    if ($LASTEXITCODE -ne 0) { throw 'Build Tools install failed' }
} else {
    throw 'winget not found: install "Build Tools for Visual Studio" with "Desktop development with C++", then rerun'
}

# 3. Python and .venv
Step 'Python'
if ($Check) {
    if (-not (Test-Path .venv)) { $missing += '.venv' }
} else {
    uv python install
    if (-not (Test-Path .venv)) { uv venv --seed .venv }
}

# 4. Packages and the C++ module
if (-not $Check) {
    Step 'pios-algo (compiles the C++ module)'
    $uvArgs = @('pip', 'install', '--python', '.venv\Scripts\python.exe', '-e', '.[dev]')
    if ($Upgrade) { $uvArgs += '--upgrade' }
    uv @uvArgs
    if ($LASTEXITCODE -ne 0) { throw 'install failed: see the CMake output above' }
}

# 5. Is the C++ module importable?
Step 'C++ module'
$py = '.venv\Scripts\python.exe'
$found = $false
if (Test-Path $py) {
    & $py -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('pios_algo_compute') else 1)"
    $found = ($LASTEXITCODE -eq 0)
}
if ($found) { Write-Host 'pios_algo_compute is built' } else { $missing += 'C++ module not built' }

if ($missing.Count -gt 0) {
    Write-Warning ('Missing: ' + ($missing -join ', ') + '. Run: powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1')
    exit 1
}
Write-Host 'Ready. Activate with .venv\Scripts\activate, then run the checks in the README.'
