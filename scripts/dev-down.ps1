# dev-down.ps1 — Detiene los servicios arrancados por dev-up.ps1 (Windows).
#
# Solo mata los procesos registrados en `.dev-pids` (los que levantó el script),
# para no tocar otros Python/Node del sistema. Los contenedores Docker quedan
# arriba por defecto (los datos persisten); usa -InfraDown para pararlos también.
#
# Uso:
#   .\scripts\dev-down.ps1            # copia de seguridad + para gateway, ai-parser, worker y web
#   .\scripts\dev-down.ps1 -InfraDown # además, docker compose down
#   .\scripts\dev-down.ps1 -NoBackup  # sin copia de seguridad (p. ej. al reiniciar tras un cambio)
#
param(
    [switch]$InfraDown,
    [switch]$NoBackup
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path "$PSScriptRoot\..").Path
$pidFile = Join-Path $root ".dev-pids"

# Copia de seguridad al parar (antes de apagar el PC): el proyecto es local, así que este es
# el momento natural. Se omite con -NoBackup. Si falla, avisa pero no impide parar la app.
if (-not $NoBackup) {
    $pgRunning = docker ps --filter "name=^traingapp-postgres$" --format "{{.Names}}" 2>$null
    if ($pgRunning -eq "traingapp-postgres") {
        Write-Host "Copia de seguridad de la base de datos..." -ForegroundColor Cyan
        try {
            & (Join-Path $PSScriptRoot "backup-db.ps1")
        } catch {
            Write-Host "  No se pudo hacer la copia: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "Postgres no está en marcha: no se hace copia de seguridad." -ForegroundColor Yellow
    }
}

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

$tsMarker = Join-Path $root ".dev-tailscale"
if (Test-Path $tsMarker) {
    $tsExe = (Get-Command tailscale -ErrorAction SilentlyContinue).Source
    if (-not $tsExe) { $tsExe = "C:\Program Files\Tailscale\tailscale.exe" }
    if (Test-Path $tsExe) {
        & $tsExe serve reset | Out-Null
        Write-Host "Publicación en Tailscale retirada." -ForegroundColor Green
    }
    Remove-Item $tsMarker -Force
}

if ($InfraDown) {
    docker compose -f (Join-Path $root "infra\docker-compose.yml") down
}
