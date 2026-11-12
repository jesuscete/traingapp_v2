# register-backup-task.ps1 — Programa la copia de seguridad diaria en el Programador de tareas.
#
# Crea (o reemplaza) la tarea "TraingApp backup" que ejecuta backup-db.ps1 cada día a la hora
# indicada. Si el PC está apagado a esa hora, se ejecuta al encenderlo. No necesita
# permisos de administrador (la tarea es de tu usuario).
#
# Uso:
#   .\scripts\register-backup-task.ps1              # a las 22:00
#   .\scripts\register-backup-task.ps1 -At 14:30
#   .\scripts\register-backup-task.ps1 -Remove      # quitar la tarea

param(
    [string]$At = "22:00",
    [switch]$Remove
)

$ErrorActionPreference = "Stop"
$taskName = "TraingApp backup"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "Tarea '$taskName' eliminada." -ForegroundColor Green
    exit 0
}

$script = Join-Path $PSScriptRoot "backup-db.ps1"
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`""
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopIfGoingOnBatteries `
    -AllowStartIfOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 15)

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
    -Settings $settings -Description "Copia diaria de la base de datos de TraingApp" -Force | Out-Null
Write-Host "Tarea '$taskName' programada cada día a las $At (copias en backups\)." -ForegroundColor Green
