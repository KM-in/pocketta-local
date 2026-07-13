param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

if ($Clean) {
    Remove-Item -Recurse -Force .venv -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force frontend/node_modules -ErrorAction SilentlyContinue
}

if (Test-Path .venv) {
    Write-Host "Using existing .venv. Pass -Clean to recreate it."
} else {
    py -3.11 -m venv .venv
}

& .venv/Scripts/python.exe -m pip install -r backend/requirements-dev.txt
Push-Location frontend
npm ci
Pop-Location
Write-Host "Project-local dependencies are ready."
