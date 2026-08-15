# dev-down.ps1 — Detiene los servicios arrancados por dev-up.ps1 (Windows).
#
# Solo mata los procesos registrados en `.dev-pids` (los que levantó el script),
# para no tocar otros Python/Node del sistema. Los contenedores Docker quedan
# arriba por defecto (los datos persisten); usa -InfraDown para pararlos también.
#
# Uso:
#   .\scripts\dev-down.ps1            # para gateway, ai-parser, worker y web
#   .\scripts\dev-down.ps1 -InfraDown # además, docker compose down
#
param(
    [switch]$InfraDown
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path "$PSScriptRoot\..").Path
$pidFile = Join-Path $root ".dev-pids"

if (Test-Path $pidFile) {
    Write-Host "Deteniendo procesos registrados en .dev-pids..." -ForegroundColor Cyan
    foreach ($id in (Get-Content $pidFile)) {
        if (Get-Process -Id $id -ErrorAction SilentlyContinue) {
            & taskkill /PID $id /T /F 2>$null | Out-Null
            Write-Host "  Detenido PID $id" -ForegroundColor Green
        } else {
            Write-Host "  PID $id ya no existe" -ForegroundColor Yellow
        }
    }
    Remove-Item $pidFile -Force
} else {
    Write-Host "No hay procesos registrados (no se detuvo nada)." -ForegroundColor Yellow
}

if ($InfraDown) {
    docker compose -f (Join-Path $root "infra\docker-compose.yml") down
}
