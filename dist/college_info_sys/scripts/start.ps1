# ============================================================================
#  АВТОМАТИЧЕСКИЙ ЗАПУСК ИС КОЛЛЕДЖА
#  Проверяет окружение, готовит базу данных и запускает сервер.
#  Запуск: powershell -ExecutionPolicy Bypass -File scripts\start.ps1
#  либо двойным щелчком по start.bat
# ============================================================================
param(
    [int]$Port = 8000,
    [switch]$NoBrowser,      # не открывать браузер
    [switch]$SkipDemo        # не заполнять демо-данные
)

$ErrorActionPreference = "Continue"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }
$ProjectRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $ProjectRoot

function Step($n, $text) { Write-Host "`n[$n] $text" -ForegroundColor Cyan }
function Ok($text)       { Write-Host "    OK  $text" -ForegroundColor Green }
function Warn($text)     { Write-Host "    !   $text" -ForegroundColor Yellow }
function Fail($text)     { Write-Host "    X   $text" -ForegroundColor Red }

Write-Host "============================================================" -ForegroundColor White
Write-Host "   ИНФОРМАЦИОННАЯ СИСТЕМА КОЛЛЕДЖА (СПО) - ЗАПУСК" -ForegroundColor White
Write-Host "============================================================" -ForegroundColor White
Write-Host "   Проект: $ProjectRoot"

# ---------------------------------------------------------------------------
# 1. Виртуальное окружение
# ---------------------------------------------------------------------------
Step "1/7" "Проверка виртуального окружения"
$venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $venvPython)) {
    Warn "Виртуальное окружение не найдено - создаю..."
    $sysPython = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $sysPython) {
        Fail "Python не найден в PATH. Установите Python 3.12+ и повторите."
        Read-Host "Нажмите Enter для выхода"; exit 1
    }
    & $sysPython -m venv (Join-Path $ProjectRoot ".venv")
    if (-not (Test-Path -LiteralPath $venvPython)) {
        Fail "Не удалось создать виртуальное окружение."
        Read-Host "Нажмите Enter для выхода"; exit 1
    }
    Ok "Виртуальное окружение создано"
    Write-Host "    Установка зависимостей (может занять минуту)..."
    & $venvPython -m pip install --upgrade pip --quiet
    & $venvPython -m pip install -r (Join-Path $ProjectRoot "requirements.txt") --quiet
    Ok "Зависимости установлены"
} else {
    Ok "Виртуальное окружение найдено"
}

# ---------------------------------------------------------------------------
# 2. Файл параметров .env
# ---------------------------------------------------------------------------
Step "2/7" "Проверка файла параметров (.env)"
$envFile = Join-Path $ProjectRoot ".env"
$envExample = Join-Path $ProjectRoot ".env.example"
if (-not (Test-Path -LiteralPath $envFile)) {
    if (Test-Path -LiteralPath $envExample) {
        # Создаём .env с безопасными локальными значениями
        $secret = & $venvPython -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
        @"
# Автоматически создан при первом запуске
DJANGO_DEBUG=True
DJANGO_SECRET_KEY=$secret
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
DB_NAME=college_sys
DB_USER=college_app
DB_PASSWORD=Coll3ge_App#2026!x7K9
DB_HOST=127.0.0.1
DB_PORT=5432
SECURE_SSL_REDIRECT=False
MASK_SENSITIVE_DATA=True
"@ | Set-Content -LiteralPath $envFile -Encoding UTF8
        Ok ".env создан (сгенерирован новый секретный ключ)"
    } else {
        Warn ".env отсутствует - используются значения по умолчанию"
    }
} else {
    Ok ".env найден"
}

# ---------------------------------------------------------------------------
# 3. Служба PostgreSQL
# ---------------------------------------------------------------------------
Step "3/7" "Проверка службы PostgreSQL"
$service = Get-Service -Name "*postgres*" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($service) {
    if ($service.Status -ne "Running") {
        Warn "Служба $($service.Name) остановлена - запускаю..."
        try { Start-Service -Name $service.Name; Start-Sleep -Seconds 3 }
        catch { Fail "Не удалось запустить службу (нужны права администратора)." }
    }
    $service.Refresh()
    if ($service.Status -eq "Running") { Ok "PostgreSQL запущен ($($service.Name))" }
    else { Fail "PostgreSQL не запущен - проверьте службу вручную." }
} else {
    Warn "Служба PostgreSQL не найдена - проверьте подключение к БД."
}

# Готовим окружение для обращения к БД
$pgBin = "C:\Program Files\PostgreSQL\17\bin"
if (Test-Path -LiteralPath (Join-Path $pgBin "pg_isready.exe")) {
    $env:Path = "$pgBin;$env:Path"
}
$env:PGPASSWORD = ""

# ---------------------------------------------------------------------------
# 4. Подключение к базе данных
# ---------------------------------------------------------------------------
Step "4/7" "Проверка подключения к базе данных"
$dbName = "college_sys"
if (Test-Path -LiteralPath $envFile) {
    $line = Get-Content -LiteralPath $envFile | Where-Object { $_ -match '^DB_NAME=' }
    if ($line) { $dbName = ($line -split '=', 2)[1].Trim() }
}

$pgIsReady = Get-Command pg_isready -ErrorAction SilentlyContinue
if ($pgIsReady) {
    & pg_isready -h 127.0.0.1 -p 5432 *> $null
    if ($LASTEXITCODE -eq 0) { Ok "Сервер БД доступен (база $dbName)" }
    else { Warn "Сервер БД не отвечает - миграции могут не примениться." }
} else {
    Warn "pg_isready недоступен - пропускаю проверку."
}

# ---------------------------------------------------------------------------
# 5. Миграции
# ---------------------------------------------------------------------------
Step "5/7" "Применение миграций базы данных"
$savedUser = $env:DB_USER
$savedPwd  = $env:DB_PASSWORD
$env:DB_USER = "postgres"     # миграции (DDL) выполняет владелец БД
$env:DB_PASSWORD = ""
& $venvPython manage.py migrate --noinput 2>&1 | Select-Object -Last 3
if ($LASTEXITCODE -eq 0) { Ok "Миграции применены" }
else { Warn "Миграции не применились (проверьте доступ к БД от владельца)." }
$env:DB_USER = $savedUser
$env:DB_PASSWORD = $savedPwd

# ---------------------------------------------------------------------------
# 6. Демонстрационные данные и администратор
# ---------------------------------------------------------------------------
Step "6/7" "Проверка данных и учётных записей"
if (-not $SkipDemo) {
    $studentCount = (& $venvPython -c @"
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
django.setup()
from contingent.models import Student
print(Student.objects.count())
"@ 2>$null) | Select-Object -Last 1

    if ($studentCount -and [int]$studentCount -gt 0) {
        Ok "Данные в базе есть (студентов: $studentCount)"
    } else {
        Warn "База пуста - заполняю демонстрационными данными..."
        & $venvPython fill_demo_data.py 2>&1 | Select-Object -Last 1
        Ok "Демонстрационные данные загружены"
    }
}

# Суперпользователь
& $venvPython -c @"
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
django.setup()
from django.contrib.auth.models import User
if not User.objects.filter(is_superuser=True).exists():
    User.objects.create_superuser('admin', 'admin@college.ru', 'admin123')
    print('created')
else:
    print('exists')
"@ 2>$null | Select-Object -Last 1 | ForEach-Object {
    if ($_ -eq 'created') { Ok "Администратор создан: admin / admin123" }
    else { Ok "Администратор существует: admin" }
}

# ---------------------------------------------------------------------------
# 7. Запуск сервера
# ---------------------------------------------------------------------------
Step "7/7" "Запуск веб-сервера"
$url = "http://127.0.0.1:$Port/"
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "   СИСТЕМА ГОТОВА К РАБОТЕ" -ForegroundColor Green
Write-Host "   Адрес:  $url" -ForegroundColor White
Write-Host "   Вход:   admin / admin123  (или кнопки быстрого входа)" -ForegroundColor White
Write-Host "   Остановка сервера: Ctrl + C" -ForegroundColor Gray
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""

if (-not $NoBrowser) {
    Start-Job -ScriptBlock {
        param($u)
        Start-Sleep -Seconds 4
        Start-Process $u
    } -ArgumentList $url | Out-Null
}

& $venvPython manage.py runserver "127.0.0.1:$Port"
