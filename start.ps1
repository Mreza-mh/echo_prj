# ============================================================
#  Echo Project — Startup Script
##    ۱) MQTT Broker (Mosquitto در Docker)   → پورت 1883
#    ۲) Kong API Gateway                     → پورت 9198 (proxy) / 9199 (admin)
#    ۳) FAISS AI Service (uvicorn)           → پورت 9000
#    ۴) Laravel API                          → پورت 8000
#    ۵) MQTT Listener (php artisan mqtt:listen)
#
#  .\start.ps1
#  .\start.ps1 -Stop
#

# cd c:\Users\SiBIRAN\Desktop\echo_prj
# docker compose -f mqtt-broker\docker-compose.yml up -d
# cd c:\Users\SiBIRAN\Desktop\echo_prj
# docker compose -f kong-gateway\docker-compose.yml up -d

# docker compose up -d برای Kong
# python -m uvicorn faiss_api:app --port 9000
# php artisan serve
# php artisan mqtt:listen

# docker compose -f kong-gateway/docker-compose.yml ps -a
# 
# ============================================================

param([switch]$Stop)

$ROOT = $PSScriptRoot

# ── توابع کمکی خروجی رنگی ───────────────────────────────────
function Step ($msg) { Write-Host "`n[$msg]" -ForegroundColor Cyan }
function Ok   ($msg) { Write-Host "  OK  $msg" -ForegroundColor Green }
function Fail ($msg) { Write-Host "  ERR $msg" -ForegroundColor Red; exit 1 }

# اجرای یک سرویس در پنجره PowerShell جدید (با عنوان مشخص برای توقف بعدی)
function Open-Window($title, $workdir, $cmd) {
    Start-Process powershell -ArgumentList `
        "-NoExit", "-Command", "cd '$workdir'; `$Host.UI.RawUI.WindowTitle='$title'; $cmd"
}

$faissDir   = Join-Path $ROOT "back\faiss"
$laravelDir = Join-Path $ROOT "back\laravel"

# ══════════════════════════════════════════════════════════════
#  حالت STOP — توقف همه سرویس‌ها
# ══════════════════════════════════════════════════════════════
if ($Stop) {
    Step "Stopping services"

    docker compose -f (Join-Path $ROOT "mqtt-broker\docker-compose.yml") down
    docker compose -f (Join-Path $ROOT "kong-gateway\docker-compose.yml") down

    foreach ($title in @("echo:faiss", "echo:laravel", "echo:mqtt-listen")) {
        Get-Process powershell -ErrorAction SilentlyContinue |
            Where-Object { $_.MainWindowTitle -like "*$title*" } |
            Stop-Process -Force -ErrorAction SilentlyContinue
    }

    Write-Host "`nHame service-ha motevaghef shodand." -ForegroundColor Cyan
    exit 0
}

# ══════════════════════════════════════════════════════════════
#  مرحله ۱ — MQTT Broker (Mosquitto در Docker)
# ══════════════════════════════════════════════════════════════
Step "Starting MQTT Broker (Mosquitto)"

docker compose -f (Join-Path $ROOT "mqtt-broker\docker-compose.yml") up -d
Ok "Mosquitto → port 1883"

# ══════════════════════════════════════════════════════════════
#  مرحله ۲ — Kong API Gateway
# ══════════════════════════════════════════════════════════════
Step "Starting Kong API Gateway"

docker compose -f (Join-Path $ROOT "kong-gateway\docker-compose.yml") up -d
Ok "Kong: proxy=9198  admin=9199  Konga=9338"

# ══════════════════════════════════════════════════════════════
#  مرحله ۳ — FAISS AI Service
# ══════════════════════════════════════════════════════════════
Step "Starting FAISS AI Service"

Open-Window "echo:faiss" $faissDir "python -m uvicorn faiss_api:app --port 9000"
Ok "FAISS API → http://localhost:9000"

# ══════════════════════════════════════════════════════════════
#  مرحله ۴ — Laravel Backend
# ══════════════════════════════════════════════════════════════
Step "Starting Laravel Backend"

Open-Window "echo:laravel" $laravelDir "php artisan serve --host=0.0.0.0 --port=8000"
Ok "Laravel API → http://localhost:8000"

# ══════════════════════════════════════════════════════════════
#  مرحله ۵ — MQTT Listener (دریافت داده حسگرها از ESP32)
# ══════════════════════════════════════════════════════════════
Step "Starting MQTT Listener"

Open-Window "echo:mqtt-listen" $laravelDir "php artisan mqtt:listen"
Ok "mqtt:listen dar hale ejra (subscribe: devices/+/data)"

# ══════════════════════════════════════════════════════════════
#  خلاصه نهایی
# ══════════════════════════════════════════════════════════════
Write-Host ""
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "  Echo project amade ast" -ForegroundColor Green
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "  MQTT Broker   :  localhost:1883" -ForegroundColor White
Write-Host "  Kong Gateway  :  proxy=9198  admin=9199  Konga=9338" -ForegroundColor White
Write-Host "  FAISS API     :  http://localhost:9000" -ForegroundColor White
Write-Host "  Laravel API   :  http://localhost:8000" -ForegroundColor White
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "  Front Angular :  cd front; npm start" -ForegroundColor Yellow
Write-Host "  Python Echo   :  cd back\python_echo; python main.py <args>" -ForegroundColor Yellow
Write-Host "  Tavaghof      :  .\start.ps1 -Stop" -ForegroundColor Yellow
Write-Host ""
