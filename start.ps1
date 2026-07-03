# ============================================================
#  Echo Project — Startup Script
#
#  چه چیزهایی را بالا می‌آورد:
#    ۱) MQTT Broker (Mosquitto در Docker)   → پورت 1883
#    ۲) Kong API Gateway                     → فعلاً غیرفعال (کامنت شده)
#    ۳) Laravel API                          → پورت 8000
#    ۴) MQTT Listener (php artisan mqtt:listen)
#
#  اجرا:   .\start.ps1
#  توقف:   .\start.ps1 -Stop
#
#  فرانت Angular جدا اجرا می‌شود:  cd front && npm start
# ============================================================

param([switch]$Stop)

$ROOT = $PSScriptRoot

# ── توابع کمکی خروجی رنگی ───────────────────────────────────
function Step ($msg) { Write-Host "`n[$msg]" -ForegroundColor Cyan }
function Ok   ($msg) { Write-Host "  OK  $msg" -ForegroundColor Green }
function Fail ($msg) { Write-Host "  ERR $msg" -ForegroundColor Red; exit 1 }
function Warn ($msg) { Write-Host "  !   $msg" -ForegroundColor Yellow }
function Info ($msg) { Write-Host "      $msg" -ForegroundColor Gray }

# اجرای یک سرویس در پنجره PowerShell جدید (با عنوان مشخص برای توقف بعدی)
function Open-Window($title, $workdir, $cmd) {
    Start-Process powershell -ArgumentList `
        "-NoExit", "-Command", "cd '$workdir'; `$Host.UI.RawUI.WindowTitle='$title'; $cmd"
}

# اگر پورت اشغال باشد، با پیام خطا متوقف می‌شود
function Assert-PortFree($port) {
    $used = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($used) { Fail "Port $port dar hale estefade ast. Aval azad-esh konid." }
}

# ══════════════════════════════════════════════════════════════
#  حالت STOP — توقف همه سرویس‌ها
# ══════════════════════════════════════════════════════════════
if ($Stop) {
    Step "Stopping services"

    # کانتینر MQTT
    $composeFile = Join-Path $ROOT "mqtt-broker\docker-compose.yml"
    if (Test-Path $composeFile) {
        docker compose -f $composeFile down
        Ok "MQTT broker stopped"
    }

    # پنجره‌های PowerShell که این اسکریپت باز کرده (بر اساس عنوان پنجره)
    foreach ($title in @("echo:laravel", "echo:mqtt-listen")) {
        $procs = Get-Process powershell -ErrorAction SilentlyContinue |
                 Where-Object { $_.MainWindowTitle -like "*$title*" }
        $procs | Stop-Process -Force -ErrorAction SilentlyContinue
        if ($procs) { Ok "$title stopped" }
    }

    Write-Host "`nHame service-ha motevaghef shodand." -ForegroundColor Cyan
    exit 0
}

# ══════════════════════════════════════════════════════════════
#  بررسی پیش‌نیازها
# ══════════════════════════════════════════════════════════════
Step "Checking prerequisites"

# Docker باید در حال اجرا باشد (برای بروکر MQTT)
try { $null = docker info 2>&1; Ok "Docker is running" }
catch { Fail "Docker Desktop ejra nist. Aval bazesh konid." }

# PHP باید در PATH باشد (برای لاراول)
try { $phpVer = (php --version 2>&1)[0]; Ok "PHP: $phpVer" }
catch { Fail "PHP peyda nashod. Masire php.exe ra be PATH ezafe konid." }

# فایل .env لاراول
$laravelDir = Join-Path $ROOT "back\laravel"
$laravelEnv = Join-Path $laravelDir ".env"
if (-not (Test-Path $laravelEnv)) {
    Fail "Laravel .env vojood nadarad. Copy konid:  cp back/laravel/.env.example back/laravel/.env"
}

# APP_KEY — اگر خالی بود، تولید می‌شود
if ((Get-Content $laravelEnv -Raw) -notmatch "APP_KEY=base64:") {
    Warn "APP_KEY khali ast — dar hale ejraye php artisan key:generate ..."
    Push-Location $laravelDir
    php artisan key:generate
    if (-not $?) { Fail "key:generate shekast khord." }
    Pop-Location
    Ok "APP_KEY tanzim shod"
}

# پکیج‌های Composer — اگر vendor نبود، نصب می‌شود
if (-not (Test-Path (Join-Path $laravelDir "vendor"))) {
    Warn "Pooshe vendor vojood nadarad — dar hale ejraye composer install ..."
    Push-Location $laravelDir
    composer install --no-interaction --prefer-dist
    if (-not $?) { Fail "composer install shekast khord." }
    Pop-Location
    Ok "Composer dependencies nasb shodand"
}

Ok "Hame pish-niaz-ha OK"

# ══════════════════════════════════════════════════════════════
#  مرحله ۱ — MQTT Broker (Mosquitto در Docker)
# ══════════════════════════════════════════════════════════════
Step "Starting MQTT Broker (Mosquitto)"

$brokerState = docker inspect --format "{{.State.Status}}" echo-mqtt-broker 2>$null
if ($brokerState -eq "running") {
    # بروکر از اجرای قبلی هنوز بالاست — کاری لازم نیست
    Ok "Mosquitto az ghabl dar hale ejra ast — port 1883"
} else {
    Assert-PortFree 1883

    docker compose -f (Join-Path $ROOT "mqtt-broker\docker-compose.yml") up -d
    if (-not $?) { Fail "MQTT broker bala nayamad." }

    # حداکثر ۱۰ ثانیه صبر تا کانتینر running شود
    $ready = $false
    for ($i = 0; $i -lt 10; $i++) {
        Start-Sleep 1
        if ((docker inspect --format "{{.State.Status}}" echo-mqtt-broker 2>&1) -eq "running") {
            $ready = $true; break
        }
    }
    if (-not $ready) { Fail "Container Mosquitto bad az 10 sanieh running nashod." }

    Ok "Mosquitto dar hale ejra — port 1883"
}

# ══════════════════════════════════════════════════════════════
#  مرحله ۲ — Kong API Gateway (فعلاً غیرفعال — بعداً استفاده می‌شود)
# ══════════════════════════════════════════════════════════════
# Step "Starting Kong API Gateway"
#
# $kongDir = Join-Path $ROOT "kong-gateway"
# docker compose -f "$kongDir\docker-compose.yml" up -d
# if (-not $?) { Fail "Kong Gateway bala nayamad." }
# Ok "Kong: proxy=9098  admin=9099  Konga=9338"

Info "Kong Gateway: gheyre-faal (baraye faal-sazi marhale 2 ra uncomment konid)"

# ══════════════════════════════════════════════════════════════
#  مرحله ۳ — Laravel Backend
# ══════════════════════════════════════════════════════════════
Step "Starting Laravel Backend"

Assert-PortFree 8000

# فقط هشدار — لاراول بدون MySQL بالا می‌آید ولی API کار نمی‌کند
Push-Location $laravelDir
$null = php artisan db:show --no-ansi 2>&1
if ($LASTEXITCODE -ne 0) {
    Warn "Ettesal be MySQL bargharar nashod — motmaen shavid MySQL ejra ast (tanzimat: back/laravel/.env)"
}
Pop-Location

Open-Window "echo:laravel" $laravelDir "php artisan serve --host=0.0.0.0 --port=8000"
Start-Sleep 2
Ok "Laravel API → http://localhost:8000"

# ══════════════════════════════════════════════════════════════
#  مرحله ۴ — MQTT Listener (دریافت داده حسگرها از ESP32)
# ══════════════════════════════════════════════════════════════
Step "Starting MQTT Listener"

Open-Window "echo:mqtt-listen" $laravelDir "php artisan mqtt:listen"
Start-Sleep 1
Ok "mqtt:listen dar hale ejra (subscribe: devices/+/data)"

# ══════════════════════════════════════════════════════════════
#  خلاصه نهایی
# ══════════════════════════════════════════════════════════════
Write-Host ""
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "  Echo project amade ast" -ForegroundColor Green
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "  MQTT Broker   :  localhost:1883" -ForegroundColor White
Write-Host "  Laravel API   :  http://localhost:8000" -ForegroundColor White
Write-Host "  Kong          :  (gheyre-faal)" -ForegroundColor DarkGray
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "  Front Angular :  cd front; npm start" -ForegroundColor Yellow
Write-Host "  Python Echo   :  cd back\python_echo; python main.py <args>" -ForegroundColor Yellow
Write-Host "  Tavaghof      :  .\start.ps1 -Stop" -ForegroundColor Yellow
Write-Host ""
