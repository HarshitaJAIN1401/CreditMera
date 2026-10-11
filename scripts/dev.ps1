# CreditMera Local Development Startup Script
Write-Host "Starting CreditMera Services..." -ForegroundColor Cyan

$root = Split-Path -Parent $PSScriptRoot

# Backend startup command
Write-Host "To run backend:" -ForegroundColor Green
Write-Host "  cd `"$root\backend`""
Write-Host "  ..\.venv\Scripts\uvicorn app.main:app --reload --port 8000"

# Frontend startup command
Write-Host "To run frontend:" -ForegroundColor Green
Write-Host "  cd `"$root\frontend`""
Write-Host "  npm run dev"
