# =============================================================
# Memories Backend - Setup para Windows (PowerShell 5.1+)
#
# Uso (desde la raiz de memories-backend):
#   .\setup.ps1            -> entorno para el emulador Android (por defecto)
#   .\setup.ps1 -Web       -> URLs de fotos para navegador (localhost)
#   .\setup.ps1 -Tools     -> ademas levanta Adminer (UI de la BD)
#
# Si Windows bloquea el script:
#   powershell -ExecutionPolicy Bypass -File .\setup.ps1
# =============================================================

param(
    [switch]$Web,
    [switch]$Tools
)

$ErrorActionPreference = "Continue"
$root = $PSScriptRoot
Set-Location $root

function Fail($msg, $hint) {
    Write-Host "  ERROR: $msg" -ForegroundColor Red
    if ($hint) { Write-Host "  $hint" -ForegroundColor DarkYellow }
    exit 1
}

function New-Secret([int]$length) {
    # Solo alfanumericos: van dentro de URLs (DATABASE_URL, REDIS_URL).
    $chars = [char[]]'abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    $bytes = New-Object byte[] $length
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    return -join ($bytes | ForEach-Object { $chars[$_ % $chars.Length] })
}

function Write-Utf8NoBom($path, $text) {
    $enc = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($path, $text, $enc)
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Memories Backend - Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path (Join-Path $root "docker-compose.yml"))) {
    Fail "No se encontro docker-compose.yml." "Ejecuta el script desde la raiz de memories-backend."
}

# --- 1. Docker instalado ---------------------------------------
Write-Host "[1/6] Verificando Docker..." -ForegroundColor Yellow
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Fail "Docker no esta instalado o no esta en el PATH." "Descarga Docker Desktop: https://www.docker.com/products/docker-desktop/"
}
docker compose version *> $null
if ($LASTEXITCODE -ne 0) { Fail "Docker Compose v2 no esta disponible." "Actualiza Docker Desktop." }
Write-Host "  OK: $(docker --version)" -ForegroundColor Green

# --- 2. Docker corriendo ---------------------------------------
Write-Host "[2/6] Verificando que Docker Engine este activo..." -ForegroundColor Yellow
docker info *> $null
if ($LASTEXITCODE -ne 0) { Fail "Docker no esta corriendo." "Abre Docker Desktop, espera a que diga 'Engine running' y vuelve a ejecutar." }
Write-Host "  OK: Docker Engine activo" -ForegroundColor Green

# --- 3. Line endings de los .sh (CRLF rompe el contenedor) -----
Write-Host "[3/6] Corrigiendo line endings de scripts .sh..." -ForegroundColor Yellow
Get-ChildItem -Path (Join-Path $root "scripts") -Filter *.sh -ErrorAction SilentlyContinue | ForEach-Object {
    $content = [System.IO.File]::ReadAllText($_.FullName)
    if ($content -match "`r") {
        Write-Utf8NoBom $_.FullName (($content -replace "`r`n", "`n") -replace "`r", "`n")
        Write-Host "  Convertido a LF: $($_.Name)" -ForegroundColor Green
    }
}
Write-Host "  OK: scripts listos" -ForegroundColor Green

# --- 4. .env ---------------------------------------------------
Write-Host "[4/6] Verificando .env..." -ForegroundColor Yellow
$envFile = Join-Path $root ".env"
$envExample = Join-Path $root ".env.example"

if (-not (Test-Path $envFile)) {
    if (-not (Test-Path $envExample)) { Fail "No existe .env.example para generar el .env." }

    $pg    = New-Secret 24
    $redis = New-Secret 24
    $minio = New-Secret 24
    $jwt   = New-Secret 64
    $publicEndpoint = if ($Web) { "http://localhost:9010" } else { "http://10.0.2.2:9010" }

    $text = [System.IO.File]::ReadAllText($envExample)
    $text = $text -replace '(?m)^POSTGRES_PASSWORD=.*$',   "POSTGRES_PASSWORD=$pg"
    $text = $text -replace '(?m)^DATABASE_URL=.*$',        "DATABASE_URL=postgresql+asyncpg://memories:$pg@localhost:5433/memories"
    $text = $text -replace '(?m)^REDIS_PASSWORD=.*$',      "REDIS_PASSWORD=$redis"
    $text = $text -replace '(?m)^REDIS_URL=.*$',           "REDIS_URL=redis://:$redis@localhost:6380/0"
    $text = $text -replace '(?m)^JWT_SECRET_KEY=.*$',      "JWT_SECRET_KEY=$jwt"
    $text = $text -replace '(?m)^S3_SECRET_KEY=.*$',       "S3_SECRET_KEY=$minio"
    $text = $text -replace '(?m)^MINIO_ROOT_PASSWORD=.*$', "MINIO_ROOT_PASSWORD=$minio"
    $text = $text -replace '(?m)^S3_PUBLIC_ENDPOINT=.*$',  "S3_PUBLIC_ENDPOINT=$publicEndpoint"

    Write-Utf8NoBom $envFile $text
    Write-Host "  OK: .env creado con contrasenas aleatorias" -ForegroundColor Green
    Write-Host "  S3_PUBLIC_ENDPOINT=$publicEndpoint" -ForegroundColor Green
} else {
    Write-Host "  OK: .env ya existe (no se modifica)" -ForegroundColor Green
    if ((Get-Content $envFile -Raw) -match "cambiame") {
        Write-Host "  WARN: tu .env aun tiene valores 'cambiame...'. Funciona, pero cambialos." -ForegroundColor DarkYellow
    }
}

# --- 5. Levantar servicios -------------------------------------
Write-Host "[5/6] Levantando servicios con Docker Compose..." -ForegroundColor Yellow
Write-Host ""
if ($Tools) { docker compose --profile tools up -d --build } else { docker compose up -d --build }
if ($LASTEXITCODE -ne 0) {
    Fail "Docker Compose no pudo levantar los servicios." "Revisa: docker compose logs --tail=100"
}

Write-Host ""
Write-Host "  Esperando a que la API quede 'healthy' (aplica migraciones)..." -ForegroundColor Yellow
$deadline = (Get-Date).AddMinutes(4)
$health = ""
do {
    $health = (docker inspect -f '{{.State.Health.Status}}' memories_api 2>$null)
    if ($health -eq "healthy") { break }
    Start-Sleep -Seconds 5
} while ((Get-Date) -lt $deadline)

$initExit = (docker inspect -f '{{.State.ExitCode}}' memories_minio_init 2>$null)
if ($initExit -ne "0") {
    Fail "minio-init no creo el bucket (exit $initExit)." "Revisa: docker compose logs minio-init minio"
}
if ($health -ne "healthy") {
    Fail "La API no quedo saludable (estado: $health)." "Revisa: docker compose logs --tail=200 api"
}
Write-Host "  OK: db, redis, minio y api arriba" -ForegroundColor Green

# --- 6. Superusuario -------------------------------------------
Write-Host "[6/6] Creando superusuario inicial..." -ForegroundColor Yellow
docker compose exec -T api python scripts/seed.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "  WARN: el seed fallo. Reintenta: docker compose exec api python scripts/seed.py" -ForegroundColor DarkYellow
}

# --- Resumen ---------------------------------------------------
$minioUser = ((Get-Content $envFile | Where-Object { $_ -match '^MINIO_ROOT_USER=' }) -replace '^MINIO_ROOT_USER=', '')

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Memories Backend levantado!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  API (host):      http://localhost:8001" -ForegroundColor Cyan
Write-Host "  Swagger:         http://localhost:8001/docs" -ForegroundColor Cyan
Write-Host "  Health:          http://localhost:8001/health/ready" -ForegroundColor Cyan
Write-Host "  API (emulador):  http://10.0.2.2:8001" -ForegroundColor Cyan
Write-Host "  MinIO Console:   http://localhost:9011" -ForegroundColor Cyan
if ($Tools) { Write-Host "  Adminer:         http://localhost:8081" -ForegroundColor Cyan }
Write-Host ""
Write-Host "  Superusuario (por defecto en seed.py):" -ForegroundColor Yellow
Write-Host "    Email:     admin@memories.local" -ForegroundColor White
Write-Host "    Password:  memories2026" -ForegroundColor White
Write-Host "  MinIO:       usuario $minioUser (contrasena en .env)" -ForegroundColor White
Write-Host ""
Write-Host "  Logs:     docker compose logs -f api" -ForegroundColor DarkGray
Write-Host "  Detener:  docker compose down" -ForegroundColor DarkGray
Write-Host "  Reset:    docker compose down -v   (borra los datos)" -ForegroundColor DarkGray
Write-Host ""
