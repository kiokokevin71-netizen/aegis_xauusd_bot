<#
.SYNOPSIS
    Deploys and launches AEGIS-XAUUSD Dedicated Gold Trading Bot.
#>

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Yellow
Write-Host "   AEGIS-XAUUSD // DEDICATED GOLD BOT DEPLOYMENT          " -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Yellow

if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not installed or not in PATH. Please install Python 3.10+ first."
    exit 1
}

if (-not (Test-Path ".venv")) {
    Write-Host "[1/3] Creating virtual environment (.venv)..." -ForegroundColor Yellow
    python -m venv .venv
} else {
    Write-Host "[1/3] Virtual environment (.venv) already exists." -ForegroundColor Green
}

Write-Host "[2/3] Installing dependencies..." -ForegroundColor Yellow
& .\.venv\Scripts\python.exe -m pip install --upgrade pip --quiet
& .\.venv\Scripts\pip.exe install -r requirements.txt --quiet

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "[INFO] Created .env from .env.example." -ForegroundColor Cyan
}

Write-Host "[3/3] Launching AEGIS-XAUUSD Gold Terminal on http://localhost:8501 ..." -ForegroundColor Yellow
& .\.venv\Scripts\streamlit.exe run app.py --server.port 8501 --theme.base "dark" --theme.primaryColor "#ffd700" --theme.backgroundColor "#07090f" --theme.secondaryBackgroundColor "#101420"
