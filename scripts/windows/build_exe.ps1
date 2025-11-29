<#
.SYNOPSIS
    Build the Claude Code Role Play Windows executable.

.DESCRIPTION
    This script builds a single Windows EXE that includes:
    - The FastAPI backend (bundled with PyInstaller)
    - The React frontend (pre-built and served statically)
    - Default agent configurations
    - All required dependencies

.PARAMETER SkipFrontend
    Skip building the frontend (use existing dist folder)

.PARAMETER Clean
    Clean build artifacts before building

.EXAMPLE
    .\build_exe.ps1
    .\build_exe.ps1 -SkipFrontend
    .\build_exe.ps1 -Clean
#>

[CmdletBinding()]
param(
    [switch]$SkipFrontend,
    [switch]$Clean
)

$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $PSScriptRoot
$repoRoot = Split-Path -Parent $scriptDir

Set-Location $repoRoot

function Write-Step($message) {
    Write-Host "`n[+] $message" -ForegroundColor Cyan
}

function Write-Success($message) {
    Write-Host "[OK] $message" -ForegroundColor Green
}

function Write-Error($message) {
    Write-Host "[ERROR] $message" -ForegroundColor Red
}

# Clean previous builds if requested
if ($Clean) {
    Write-Step "Cleaning previous build artifacts..."
    if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
    if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
    Write-Success "Clean complete"
}

# Check prerequisites
Write-Step "Checking prerequisites..."

if (-not (Get-Command "uv" -ErrorAction SilentlyContinue)) {
    Write-Error "uv is not installed. Please install it first: irm https://astral.sh/uv/install.ps1 | iex"
    exit 1
}

if (-not (Get-Command "node" -ErrorAction SilentlyContinue)) {
    Write-Error "Node.js is not installed. Please install it first."
    exit 1
}

Write-Success "Prerequisites OK"

# Build frontend
if (-not $SkipFrontend) {
    Write-Step "Building frontend..."
    Push-Location "frontend"

    # Always ensure dependencies are installed (check for vite specifically)
    if (-not (Test-Path "node_modules/vite")) {
        Write-Step "Installing frontend dependencies..."
        npm install
        if ($LASTEXITCODE -ne 0) {
            Pop-Location
            Write-Error "npm install failed"
            exit 1
        }
    }

    npm run build
    if ($LASTEXITCODE -ne 0) {
        Pop-Location
        Write-Error "Frontend build failed"
        exit 1
    }
    Pop-Location

    if (-not (Test-Path "frontend/dist/index.html")) {
        Write-Error "Frontend build failed - dist/index.html not found"
        exit 1
    }
    Write-Success "Frontend built successfully"
} else {
    Write-Step "Skipping frontend build (using existing dist)"
    if (-not (Test-Path "frontend/dist/index.html")) {
        Write-Error "frontend/dist/index.html not found. Run without -SkipFrontend first."
        exit 1
    }
}

# Install PyInstaller if needed
Write-Step "Ensuring PyInstaller is installed..."
uv pip install pyinstaller --quiet

# Build the executable
Write-Step "Building Windows executable with PyInstaller..."
uv run pyinstaller ClaudeCodeRP.spec --noconfirm

# Check output
$exePath = "dist/ClaudeCodeRP.exe"
if (Test-Path $exePath) {
    $size = (Get-Item $exePath).Length / 1MB
    Write-Success "Build complete!"
    Write-Host ""
    Write-Host "Output: $exePath" -ForegroundColor Yellow
    Write-Host "Size: $([math]::Round($size, 2)) MB" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To run the application:" -ForegroundColor Cyan
    Write-Host "  1. Copy ClaudeCodeRP.exe to your desired location"
    Write-Host "  2. Create a .env file with API_KEY_HASH and JWT_SECRET"
    Write-Host "  3. Run ClaudeCodeRP.exe"
    Write-Host ""
} else {
    Write-Error "Build failed - executable not found"
    exit 1
}
