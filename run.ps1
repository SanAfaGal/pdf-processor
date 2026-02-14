# Run PDF Processor using the project venv.
# Usage: .\run.ps1

$venv = Join-Path $PSScriptRoot ".venv"
$py = Join-Path $venv "Scripts\python.exe"

if (-not (Test-Path $py)) {
    Write-Host "No se encontró el entorno virtual. Cree uno con:"
    Write-Host "  python -m venv .venv"
    Write-Host "  .\.venv\Scripts\Activate.ps1"
    Write-Host "  pip install -r requirements.txt"
    exit 1
}

& $py (Join-Path $PSScriptRoot "main.py") @args
