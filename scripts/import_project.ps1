# ============================================================================
#  РАЗВЁРТЫВАНИЕ ИС КОЛЛЕДЖА на новой машине
#  Восстанавливает базу данных из дампа и запускает систему.
#  Запуск: powershell -ExecutionPolicy Bypass -File scripts\import_project.ps1
# ============================================================================
param(
    [string]$DumpFile = "",
    [string]$DbName = "college_sys",
    [string]$DbUser = "postgres",
    [switch]$SkipServer      # только восстановить БД, не запускать сервер
)

$ErrorActionPreference = "Continue"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }
$ProjectRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $ProjectRoot

function Step($t) { Write-Host "`n>> $t" -ForegroundColor Cyan }
function Ok($t)   { Write-Host "   OK  $t" -ForegroundColor Green }
function Warn($t) { Write-Host "   !   $t" -ForegroundColor Yellow }
function Fail($t) { Write-Host "   X   $t" -ForegroundColor Red }

Write-Host "============================================================" -ForegroundColor White
Write-Host "   РАЗВЁРТЫВАНИЕ ИС КОЛЛЕДЖА" -ForegroundColor White
Write-Host "============================================================" -ForegroundColor White

$pgBin = "C:\Program Files\PostgreSQL\17\bin"
if (Test-Path -LiteralPath $pgBin) { $env:Path = "$pgBin;$env:Path" }

# ---------------------------------------------------------------------------
# 1. Автопоиск дампа
# ---------------------------------------------------------------------------
Step "1/4 Поиск дампа базы данных"
if (-not $DumpFile) {
    $candidates = @(
        (Join-Path $ProjectRoot "database_dump.sql"),
        (Join-Path $ProjectRoot "..\database_dump.sql")
    )
    foreach ($c in $candidates) {
        if (Test-Path -LiteralPath $c) { $DumpFile = (Resolve-Path -LiteralPath $c).Path; break }
    }
}
if (-not $DumpFile -or -not (Test-Path -LiteralPath $DumpFile)) {
    Warn "Дамп не найден. Укажите путь: -DumpFile C:\path\database_dump.sql"
    Warn "Система будет развёрнута с пустой базой (демо-данные - fill_demo_data.py)."
} else {
    Ok "Дамп найден: $DumpFile"
}

# ---------------------------------------------------------------------------
# 2. Проверка службы PostgreSQL
# ---------------------------------------------------------------------------
Step "2/4 Проверка PostgreSQL"
$service = Get-Service -Name "*postgres*" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($service) {
    if ($service.Status -ne "Running") {
        Warn "Служба остановлена - запускаю..."
        try { Start-Service -Name $service.Name; Start-Sleep -Seconds 3 } catch {
            Fail "Запустите службу PostgreSQL вручную (нужны права администратора)"
        }
    }
    $service.Refresh()
    if ($service.Status -eq "Running") { Ok "PostgreSQL запущен" }
} else {
    Fail "PostgreSQL не найден. Установите: https://www.postgresql.org/download/windows/"
    Read-Host "Нажмите Enter для выхода"; exit 1
}

# ---------------------------------------------------------------------------
# 3. Создание БД и восстановление данных
# ---------------------------------------------------------------------------
Step "3/4 Создание базы и восстановление данных"
$env:PGPASSWORD = ""

# Проверяем, существует ли база
$exists = & psql -U $DbUser -h 127.0.0.1 -tAc "SELECT 1 FROM pg_database WHERE datname='$DbName'" 2>$null
if ($exists -eq "1") {
    Ok "База $DbName уже существует (данные будут дополнены)"
} else {
    & psql -U $DbUser -h 127.0.0.1 -c "CREATE DATABASE $DbName ENCODING 'UTF8' TEMPLATE template0" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) { Ok "База $DbName создана" } else { Fail "Не удалось создать базу" }
}

if ($DumpFile -and (Test-Path -LiteralPath $DumpFile)) {
    Write-Host "   Восстановление данных из дампа..."
    & psql -U $DbUser -h 127.0.0.1 -d $DbName -f $DumpFile 2>&1 | Select-Object -Last 2
    if ($LASTEXITCODE -eq 0) { Ok "Данные восстановлены" }
    else { Warn "Восстановление завершилось с предупреждениями (возможно, данные уже есть)" }
}

# ---------------------------------------------------------------------------
# 4. Запуск системы
# ---------------------------------------------------------------------------
Step "4/4 Запуск системы"
if ($SkipServer) {
    Ok "Готово. Запустите систему: start.bat"
} else {
    Write-Host "   Запуск через start.ps1 (создаст окружение и поднимет сервер)..." -ForegroundColor Gray
    & (Join-Path $PSScriptRoot "start.ps1")
}
