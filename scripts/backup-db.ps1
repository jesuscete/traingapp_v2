# backup-db.ps1 — Copia de seguridad de la base de datos de TraingApp (Postgres en Docker).
#
# Genera backups\traingapp-AAAAMMDD-HHmm.dump (formato custom de pg_dump) y conserva las
# últimas -Keep copias (14 por defecto). Pensado para ejecutarse a diario con
# register-backup-task.ps1, pero se puede lanzar a mano en cualquier momento.
#
# Uso:
#   .\scripts\backup-db.ps1
#   .\scripts\backup-db.ps1 -Keep 30
#
# Restaurar: .\scripts\restore-db.ps1 -File backups\traingapp-AAAAMMDD-HHmm.dump

param(
    [int]$Keep = 14,
    [string]$Container = "traingapp-postgres",
    [string]$Database = "traingapp",
    [string]$User = "traingapp"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$backupDir = Join-Path $root "backups"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

$running = docker ps --filter "name=^$Container$" --format "{{.Names}}"
if ($running -ne $Container) {
    throw "El contenedor $Container no está en marcha. Arranca Docker y la infraestructura antes."
}

$stamp = Get-Date -Format "yyyyMMdd-HHmm"
$name = "traingapp-$stamp.dump"
$target = Join-Path $backupDir $name

# pg_dump escribe dentro del contenedor y se copia fuera: redirigir binarios en
# PowerShell 5.1 los corrompe.
docker exec $Container pg_dump -U $User -d $Database -Fc -f "/tmp/$name"
if ($LASTEXITCODE -ne 0) { throw "pg_dump ha fallado (código $LASTEXITCODE)" }
docker cp "${Container}:/tmp/$name" $target
if ($LASTEXITCODE -ne 0) { throw "No se pudo copiar la copia fuera del contenedor" }
docker exec $Container rm -f "/tmp/$name" | Out-Null

$size = [math]::Round((Get-Item $target).Length / 1KB)
Write-Host "Copia creada: backups\$name ($size KB)" -ForegroundColor Green

$old = Get-ChildItem $backupDir -Filter "traingapp-*.dump" |
    Where-Object { $_.Name -match '^traingapp-\d{8}-\d{4}\.dump$' } |
    Sort-Object Name -Descending |
    Select-Object -Skip $Keep
foreach ($file in $old) {
    Remove-Item $file.FullName -Force
    Write-Host "  Borrada copia antigua: $($file.Name)" -ForegroundColor DarkGray
}
