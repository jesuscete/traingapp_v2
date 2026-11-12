# restore-db.ps1 — Restaura una copia de backups\ sobre la base de datos de TraingApp.
#
# ¡Sustituye TODOS los datos actuales por los de la copia! Antes hace una copia de
# seguridad del estado actual por si acaso. Para el backend antes de restaurar
# (.\scripts\dev-down.ps1) y vuelve a arrancarlo después.
#
# Uso:
#   .\scripts\restore-db.ps1 -File backups\traingapp-20261112-2200.dump

param(
    [Parameter(Mandatory = $true)][string]$File,
    [string]$Container = "traingapp-postgres",
    [string]$Database = "traingapp",
    [string]$User = "traingapp"
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path $File)) { throw "No existe el archivo $File" }

$answer = Read-Host "Esto sustituye todos los datos actuales por los de $File. Escribe SI para continuar"
if ($answer -ne "SI") { Write-Host "Cancelado."; exit 1 }

& (Join-Path $PSScriptRoot "backup-db.ps1") -Keep 1000

$name = Split-Path -Leaf $File
docker cp $File "${Container}:/tmp/$name"
if ($LASTEXITCODE -ne 0) { throw "No se pudo copiar la copia al contenedor" }
docker exec $Container pg_restore -U $User -d $Database --clean --if-exists --no-owner "/tmp/$name"
$code = $LASTEXITCODE
docker exec $Container rm -f "/tmp/$name" | Out-Null
if ($code -ne 0) { throw "pg_restore terminó con errores (código $code)" }
Write-Host "Restaurado desde $File. Arranca de nuevo con .\scripts\dev-up.ps1" -ForegroundColor Green
