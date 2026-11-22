$ErrorActionPreference = "Stop"

python -m pip install -r requirements-build.txt
python -m PyInstaller --noconfirm --clean "CV Analyzer Pro.spec"

$executable = Join-Path $PSScriptRoot "dist\CV Analyzer Pro.exe"
if (-not (Test-Path -LiteralPath $executable)) {
    throw "No se generó el ejecutable esperado: $executable"
}

Write-Host "Ejecutable creado: $executable"
