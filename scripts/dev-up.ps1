# dev-up.ps1 — Arranca la infraestructura y los servicios de TraingApp v2 en local (Windows).
#
# Levanta, en orden:
#   1. Infraestructura Docker (Postgres :5432 + Redis :6379)  — omisible con -SkipInfra
#   2. Migraciones Alembic                                     — omisible con -SkipMigrations
#   3. api-gateway (:8000), ai-parser (:8100), worker (cola Redis), web (:3000)
#
# Idempotente: si un puerto ya está en uso, ese servicio se omite (no se duplica).
# Los PIDs lanzados por este script se guardan en `.dev-pids` para poder pararlos con dev-down.ps1.
#
# Uso:
#   .\scripts\dev-up.ps1             # todo
#   .\scripts\dev-up.ps1 -SkipInfra  # solo servicios (si ya hay contenedores arriba)
#   .\scripts\dev-up.ps1 -Lan        # accesible desde el móvil en la red local (IP autodetectada)
#   .\scripts\dev-up.ps1 -Lan -LanIp 192.168.1.50
#   .\scripts\dev-up.ps1 -Https      # LAN + HTTPS (PWA instalable y pantalla siempre encendida)
#
# -Lan expone api-gateway (:8000) y web (:3000) en la red local: úsalo solo en redes de confianza.
# -Https requiere mkcert (una vez):  winget install FiloSottile.mkcert ; mkcert -install
#   y en el móvil instalar como certificado de CA el fichero rootCA.pem de `mkcert -CAROOT`.
#
param(
    [switch]$SkipInfra,
    [switch]$SkipMigrations,
    [switch]$Lan,
    [string]$LanIp,
    [switch]$Https
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path "$PSScriptRoot\..").Path
$pidFile = Join-Path $root ".dev-pids"
$nodeExe = "E:\nodejs\node.exe"
$bindHost = "127.0.0.1"
$webArgs = @("node_modules\next\dist\bin\next", "dev")
$gatewayArgs = @("-m", "uvicorn", "app.main:app", "--host", $bindHost, "--port", "8000")
$scheme = "http"
if ($Https) { $Lan = $true }

if ($Lan) {
    if (-not $LanIp) {
        $LanIp = (Get-NetIPAddress -AddressFamily IPv4 |
            Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" -and $_.PrefixOrigin -in @("Dhcp", "Manual") } |
            Select-Object -First 1).IPAddress
    }
    if (-not $LanIp) { throw "No se pudo detectar la IP local. Pásala con -LanIp." }
    $bindHost = "0.0.0.0"
    $webArgs = @("node_modules\next\dist\bin\next", "dev", "-H", "0.0.0.0")
    $gatewayArgs = @("-m", "uvicorn", "app.main:app", "--host", $bindHost, "--port", "8000")

    if ($Https) {
        if (-not (Get-Command mkcert -ErrorAction SilentlyContinue)) {
            throw "Falta mkcert. Instálalo con: winget install FiloSottile.mkcert ; mkcert -install"
        }
        $certDir = Join-Path $root ".certs"
        New-Item -ItemType Directory -Force -Path $certDir | Out-Null
        $cert = Join-Path $certDir "dev.pem"
        $key = Join-Path $certDir "dev-key.pem"
        $ipFile = Join-Path $certDir "ip.txt"
        $previousIp = if (Test-Path $ipFile) { (Get-Content $ipFile -Raw).Trim() } else { "" }
        if (-not (Test-Path $cert) -or $previousIp -ne $LanIp) {
            & mkcert -cert-file $cert -key-file $key localhost 127.0.0.1 $LanIp
            if ($LASTEXITCODE -ne 0) { throw "mkcert no pudo generar el certificado." }
            Set-Content -Path $ipFile -Value $LanIp
        }
        $scheme = "https"
        $gatewayArgs += @("--ssl-certfile", $cert, "--ssl-keyfile", $key)
        $webArgs += @("--experimental-https", "--experimental-https-cert", $cert, "--experimental-https-key", $key)
    }

    # Los procesos hijos heredan estas variables.
    $env:APP_CORS_ORIGINS = "${scheme}://localhost:3000,${scheme}://127.0.0.1:3000,${scheme}://${LanIp}:3000"
    $env:NEXT_PUBLIC_API_URL = "${scheme}://${LanIp}:8000"
    $env:LAN_DEV_ORIGIN = $LanIp
    Write-Host "Modo LAN: abre ${scheme}://${LanIp}:3000 en el móvil (misma red Wi-Fi)." -ForegroundColor Cyan
    if ($Https) {
        Write-Host "  Certificado raíz para el móvil: $(& mkcert -CAROOT)\rootCA.pem" -ForegroundColor Cyan
    }
}

$services = @(
    @{ Name = "api-gateway"; Port = 8000; File = "$root\services\api-gateway\.venv\Scripts\python.exe"; Args = $gatewayArgs; WorkDir = "$root\services\api-gateway"; Log = "uvicorn"; Health = "${scheme}://127.0.0.1:8000/health"; Tries = 30 },
    @{ Name = "ai-parser";   Port = 8100; File = "$root\services\ai-parser\.venv\Scripts\python.exe";     Args = @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8100"); WorkDir = "$root\services\ai-parser";     Log = "ai-parser"; Health = "http://127.0.0.1:8100/health"; Tries = 30 },
    @{ Name = "worker";      Port = $null; File = "$root\services\ai-parser\.venv\Scripts\python.exe";     Args = @("-m", "app.worker");                                                 WorkDir = "$root\services\ai-parser";     Log = "worker";      Health = $null; Tries = 0 },
    @{ Name = "web";         Port = 3000; File = $nodeExe;                                                Args = $webArgs;                                                                 WorkDir = "$root\services\web";           Log = "next";       Health = "${scheme}://localhost:3000";      Tries = 90 }
)

function Test-PortInUse {
    param([int]$Port)
    if (-not $Port) { return $false }
    return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

function Test-WorkerRunning {
    return [bool](Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like "*app.worker*" })
}

function Wait-Health {
    param([string]$Url, [int]$Tries)
    for ($i = 1; $i -le $Tries; $i++) {
        try {
            $response = Invoke-WebRequest -Uri $Url -TimeoutSec 2 -UseBasicParsing
            if ($response.StatusCode -eq 200) {
                Write-Host "  [$Url] OK" -ForegroundColor Green
                return
            }
        } catch { }
        Start-Sleep -Seconds 1
    }
    Write-Host "  [$Url] no responde tras $Tries intentos" -ForegroundColor Red
}

# --- Limpieza de PIDs huérfanos del fichero de seguimiento ---
if (Test-Path $pidFile) {
    $live = @()
    foreach ($id in (Get-Content $pidFile)) {
        if (Get-Process -Id $id -ErrorAction SilentlyContinue) { $live += $id }
    }
    if ($live.Count) { Set-Content -LiteralPath $pidFile -Value $live } else { Remove-Item $pidFile -Force }
}

Write-Host "== TraingApp v2 — arranque local ==" -ForegroundColor Cyan

# --- 1. Infraestructura Docker ---
if (-not $SkipInfra) {
    Write-Host "[1/4] Infraestructura (Postgres + Redis)..." -ForegroundColor Cyan
    docker compose -f (Join-Path $root "infra\docker-compose.yml") up -d
    if ($LASTEXITCODE -ne 0) { throw "docker compose up -d falló (¿Docker Desktop en ejecución?)" }
    $pgReady = $false
    for ($i = 0; $i -lt 30; $i++) {
        if (Test-PortInUse -Port 5432) { $pgReady = $true; break }
        Start-Sleep -Seconds 1
    }
    if (-not $pgReady) { Write-Host "  Postgres no escucha en :5432 tras 30s" -ForegroundColor Red }
}

# --- 2. Migraciones ---
if (-not $SkipMigrations) {
    Write-Host "[2/4] Migraciones Alembic..." -ForegroundColor Cyan
    Push-Location (Join-Path $root "services\api-gateway")
    try {
        & "$root\services\api-gateway\.venv\Scripts\python.exe" -m alembic upgrade head
        if ($LASTEXITCODE -ne 0) { throw "alembic upgrade head falló" }
    } finally { Pop-Location }
}

# --- 3. Servicios ---
Write-Host "[3/4] Arrancando servicios..." -ForegroundColor Cyan
foreach ($service in $services) {
    $name = $service.Name
    if ($name -eq "worker") {
        if (Test-WorkerRunning) {
            Write-Host "  [$name] ya hay un worker corriendo - se omite." -ForegroundColor Yellow
            continue
        }
    } elseif (Test-PortInUse -Port $service.Port) {
        Write-Host "  [$name] ya escucha en :$($service.Port) - se omite." -ForegroundColor Yellow
        continue
    }

    $logDir = Join-Path $root "logs"
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
    $outLog = Join-Path $logDir "$($service.Log).log"
    $errLog = Join-Path $logDir "$($service.Log).err.log"
    $process = Start-Process -FilePath $service.File -ArgumentList $service.Args `
        -WorkingDirectory $service.WorkDir -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput $outLog -RedirectStandardError $errLog
    Start-Sleep -Milliseconds 800

    if ($process.HasExited) {
        Write-Host "  [$name] FALLO al arrancar (exit $($process.ExitCode)). Revisa: $errLog" -ForegroundColor Red
        exit 1
    }
    Add-Content -LiteralPath $pidFile -Value "$($process.Id)"
    Write-Host "  [$name] arrancado (PID $($process.Id)). Log: logs\$($service.Log).log" -ForegroundColor Green
}

# --- 4. Health checks ---
Write-Host "[4/4] Verificación de salud..." -ForegroundColor Cyan
foreach ($service in $services) {
    if ($service.Health) { Wait-Health -Url $service.Health -Tries $service.Tries }
}

Write-Host "`nListo. Web: http://localhost:3000 — Para detener: .\scripts\dev-down.ps1" -ForegroundColor Green
