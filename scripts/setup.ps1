<#
.SYNOPSIS
    Sets RETRACK Studio up on Windows: virtual environment, dependencies, checks.

.DESCRIPTION
    Creates .venv with a supported Python, installs RETRACK and the extras you
    choose, and finishes by running `retrack doctor` so you can see exactly
    what the machine can do.

.EXAMPLE
    .\scripts\setup.ps1
    .\scripts\setup.ps1 -Full
    .\scripts\setup.ps1 -Extras "gui,live" -SkipTorch
#>
[CmdletBinding()]
param(
    [string]$Extras = "gui,live,reports",
    [switch]$Full,
    [switch]$SkipTorch,
    [string]$PythonVersion = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Write-Step($text) { Write-Host "`n=== $text" -ForegroundColor Cyan }
function Write-Ok($text)   { Write-Host "  OK  $text" -ForegroundColor Green }
function Write-Warn($text) { Write-Host "  !   $text" -ForegroundColor Yellow }

Write-Host "RETRACK Studio — Windows setup" -ForegroundColor White

# ---------------------------------------------------------------------------
Write-Step "Finding a supported Python"

# librosa depends on numba, which lags each new Python release by months.
# Prefer the versions known to work rather than whatever `python` points at.
$preferred = if ($PythonVersion) { @($PythonVersion) } else { @("3.12", "3.11", "3.10") }
$python = $null

foreach ($version in $preferred) {
    try {
        $probe = & py "-$version" -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $probe) {
            $python = @("py", "-$version")
            Write-Ok "Python $version at $probe"
            break
        }
    } catch { }
}

if (-not $python) {
    Write-Warn "No Python 3.10-3.12 found via the py launcher; falling back to 'python'"
    $version = & python -c "import sys; print('.'.join(map(str, sys.version_info[:2])))"
    if ($LASTEXITCODE -ne 0) {
        throw "No Python found. Install 3.11 or 3.12 from https://python.org"
    }
    Write-Warn "Using Python $version — if librosa fails to install, this is why"
    $python = @("python")
}

# ---------------------------------------------------------------------------
Write-Step "Creating the virtual environment"

if (Test-Path ".venv") {
    Write-Ok ".venv already exists, reusing it"
} else {
    & $python[0] $python[1..($python.Length-1)] -m venv .venv
    Write-Ok "created .venv"
}

$venvPython = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) { throw "virtual environment is broken: $venvPython not found" }

# ---------------------------------------------------------------------------
Write-Step "Installing RETRACK"

& $venvPython -m pip install --upgrade pip --quiet
Write-Ok "pip updated"

if ($Full) { $Extras = "gui,live,reports,ai,plugins,mir,llm" }
Write-Host "  extras: $Extras"

& $venvPython -m pip install -e ".[$Extras]"
if ($LASTEXITCODE -ne 0) { throw "installation failed" }
Write-Ok "RETRACK installed"

# ---------------------------------------------------------------------------
Write-Step "Checking FFmpeg"

if (Get-Command ffmpeg -ErrorAction SilentlyContinue) {
    Write-Ok "FFmpeg is on PATH"
} else {
    Write-Warn "FFmpeg not found — only WAV/FLAC/OGG will load"
    Write-Host "      Install with:  winget install Gyan.FFmpeg"
}

# ---------------------------------------------------------------------------
if (-not $SkipTorch) {
    Write-Step "GPU acceleration"
    if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
        $gpu = (& nvidia-smi --query-gpu=name --format=csv,noheader) -join ", "
        Write-Host "  found: $gpu"
        $answer = Read-Host "  Install the CUDA build of PyTorch? (10-20x faster separation) [Y/n]"
        if ($answer -ne "n" -and $answer -ne "N") {
            & $venvPython scripts\install_torch.py
            & $venvPython -m pip install -e ".[ai]"
            Write-Ok "GPU stack installed"
        }
    } else {
        Write-Warn "no NVIDIA GPU detected — everything runs on CPU"
    }
}

# ---------------------------------------------------------------------------
Write-Step "Generating the demo track"
& $venvPython examples\generate_demo_track.py
Write-Ok "demo rendered to examples\generated\"

# ---------------------------------------------------------------------------
Write-Step "System check"
& $venvPython -m retrack doctor

# ---------------------------------------------------------------------------
Write-Host "`n=== Ready" -ForegroundColor Green
Write-Host @"

Activate the environment:
    .venv\Scripts\Activate.ps1

Then try:
    retrack gui
    retrack analyze examples\generated\retrack_demo_techhouse.wav
    retrack report  examples\generated\retrack_demo_techhouse.wav --out reports

"@
