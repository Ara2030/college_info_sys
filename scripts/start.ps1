# ============================================================================
#  АВТОМАТИЧЕСКИЙ ЗАПУСК ИС КОЛЛЕДЖА
#  Проверяет окружение, готовит базу данных и запускает сервер.
#  Запуск: powershell -ExecutionPolicy Bypass -File scripts\start.ps1
#  либо двойным щелчком по start.bat
# ============================================================================
param(
    [int]$Port = 8000,
    [switch]$NoBrowser,      # не открывать браузер
    [switch]$SkipDemo,       # не заполнять демо-данные
    [switch]$SkipUpdate      # не проверять обновления при старте
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

# Целостность проекта: скрипт должен лежать внутри папки проекта
if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot "manage.py"))) {
    Fail "Не найден manage.py в папке проекта."
    Write-Host "    Скопируйте папку проекта целиком (со скриптами) и запустите start.bat заново." -ForegroundColor Yellow
    Read-Host "Нажмите Enter для выхода"; exit 1
}

# ---------------------------------------------------------------------------
# Вспомогательные функции проверки Python
# ---------------------------------------------------------------------------
# venv считается рабочим, только если python.exe реально запускается.
# Файл может существовать, но указывать на удалённый базовый Python —
# тогда все вызовы молча падают и система "не запускается".
function Test-PythonWorks {
    param([string]$Path)
    if (-not $Path -or -not (Test-Path -LiteralPath $Path)) { return $false }
    try {
        $out = & $Path -c "import sys; print('py-ok')" 2>&1
        return ($LASTEXITCODE -eq 0 -and ("$out" -match 'py-ok'))
    } catch {
        return $false
    }
}

# Ставит зависимости проекта. Если в комплекте установки есть локальные колёса
# (_install\wheels) - работает офлайн, без интернета.
function Install-Requirements {
    param([string]$VenvPython, [string]$Root)
    $pipArgs = @("-m", "pip", "install", "--quiet", "--disable-pip-version-check",
                 "-r", (Join-Path $Root "requirements.txt"))
    $wheels = Join-Path $Root "_install\wheels"
    if (Test-Path -LiteralPath $wheels) {
        $pipArgs += @("--no-index", "--find-links", $wheels)
        Write-Host "    Использую локальный комплект библиотек (интернет не нужен)" -ForegroundColor Gray
    }
    & $VenvPython @pipArgs
    return $LASTEXITCODE
}

# Ищем установленный базовый Python (3.10+) среди типовых мест установки.
function Find-BasePython {
    $found = @()
    $patterns = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python3*\python.exe"),
        "C:\Program Files\Python3*\python.exe",
        "C:\Program Files (x86)\Python3*\python.exe",
        "C:\Python3*\python.exe"
    )
    foreach ($p in $patterns) {
        $found += Get-ChildItem $p -ErrorAction SilentlyContinue | Sort-Object FullName -Descending
    }
    $onPath = Get-Command python -ErrorAction SilentlyContinue
    if ($onPath -and $onPath.Source -notlike "*WindowsApps*") { $found += (Get-Item $onPath.Source) }

    foreach ($exe in $found) {
        if (-not (Test-PythonWorks $exe.FullName)) { continue }
        try {
            $v = & $exe.FullName -c "import sys; print(sys.version_info[0]*100+sys.version_info[1])" 2>$null
        } catch { continue }
        if ($v -and [int]$v -ge 310) { return $exe.FullName }
    }
    return $null
}

# ---------------------------------------------------------------------------
# 1. Виртуальное окружение
# ---------------------------------------------------------------------------
Step "1/7" "Проверка виртуального окружения"
$venvDir = Join-Path $ProjectRoot ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"

if (Test-PythonWorks $venvPython) {
    $pyVer = & $venvPython -c "import sys; print('.'.join(map(str, sys.version_info[:3])))" 2>$null
    Ok "Виртуальное окружение работает (Python $pyVer)"
} else {
    if (Test-Path -LiteralPath $venvPython) {
        Warn "Виртуальное окружение повреждено: python.exe не запускается."
        Warn "Причина: базовый Python удалён или перемещён. Пересоздаю окружение..."
    } else {
        Warn "Виртуальное окружение не найдено - создаю..."
    }

    $sysPython = Find-BasePython
    if (-not $sysPython) {
        Fail "Python 3.10+ не найден в системе."
        Write-Host "    Установите его одной командой (без прав администратора):" -ForegroundColor Yellow
        Write-Host '      winget install --id Python.Python.3.14 --exact --scope user' -ForegroundColor White
        Write-Host "    либо скачайте с https://www.python.org/downloads/windows/" -ForegroundColor Yellow
        Write-Host "    После установки запустите start.bat снова." -ForegroundColor Yellow
        Read-Host "Нажмите Enter для выхода"; exit 1
    }
    Ok "Найден Python: $sysPython"

    if (Test-Path -LiteralPath $venvDir) {
        Write-Host "    Удаляю нерабочее окружение..."
        Remove-Item -LiteralPath $venvDir -Recurse -Force -ErrorAction SilentlyContinue
    }

    & $sysPython -m venv $venvDir
    if (-not (Test-PythonWorks $venvPython)) {
        Fail "Не удалось создать виртуальное окружение."
        Write-Host "    Проверьте, что Python установлен полностью (с модулем venv)." -ForegroundColor Yellow
        Read-Host "Нажмите Enter для выхода"; exit 1
    }
    Ok "Виртуальное окружение создано"

    Write-Host "    Установка зависимостей (может занять 1-2 минуты)..."
    & $venvPython -m pip install --upgrade pip --quiet
    if ((Install-Requirements $venvPython $ProjectRoot) -ne 0) {
        Fail "Не удалось установить зависимости из requirements.txt."
        Write-Host "    Проверьте подключение к интернету и запустите снова." -ForegroundColor Yellow
        Read-Host "Нажмите Enter для выхода"; exit 1
    }
    Ok "Зависимости установлены"
}

# Проверяем, что ключевые библиотеки на месте (venv мог сохраниться неполным)
& $venvPython -c "import django, psycopg, openpyxl, reportlab, lxml, PIL" *> $null
if ($LASTEXITCODE -ne 0) {
    Warn "Часть зависимостей отсутствует - устанавливаю..."
    Install-Requirements $venvPython $ProjectRoot | Out-Null
    & $venvPython -c "import django, psycopg, openpyxl, reportlab, lxml, PIL" *> $null
    if ($LASTEXITCODE -ne 0) {
        Fail "Зависимости не установились. Выполните вручную:"
        Write-Host "      .venv\Scripts\python.exe -m pip install -r requirements.txt" -ForegroundColor White
        Read-Host "Нажмите Enter для выхода"; exit 1
    }
    Ok "Зависимости установлены"
} else {
    Ok "Зависимости на месте"
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
# 2.5. Проверка обновлений (скачивает и устанавливает новую версию, если есть)
# ---------------------------------------------------------------------------
Step "2.5/7" "Проверка обновлений"
if ($SkipUpdate) {
    Ok "пропущено (-SkipUpdate)"
} else {
    $updater = Join-Path $PSScriptRoot "update.ps1"
    if (-not (Test-Path -LiteralPath $updater)) {
        Warn "модуль обновления не найден - пропускаю"
    } else {
        & $updater -ProjectRoot $ProjectRoot -Quiet
        switch ($LASTEXITCODE) {
            2 { Ok "система обновлена до новой версии" }
            3 { Warn "есть обновление, автоустановка отключена (UPDATE_AUTO=False)" }
            4 { Warn "обновление не удалось - работаю на текущей версии (logs\update.log)" }
            default { }
        }
    }
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
# Параметры администратора БД берём из .env (при установке пароль postgres задаётся)
$adminUser = "postgres"
$adminPwd = ""
if (Test-Path -LiteralPath $envFile) {
    foreach ($key in @("DB_ADMIN_USER", "DB_ADMIN_PASSWORD")) {
        $line = Get-Content -LiteralPath $envFile | Where-Object { $_ -match "^$key=" } | Select-Object -First 1
        if ($line) {
            $value = ($line -split '=', 2)[1].Trim()
            if ($key -eq "DB_ADMIN_USER") { $adminUser = $value } else { $adminPwd = $value }
        }
    }
}
$savedUser = $env:DB_USER
$savedPwd  = $env:DB_PASSWORD
$env:DB_USER = $adminUser     # миграции (DDL) выполняет владелец БД
$env:DB_PASSWORD = $adminPwd
& $venvPython manage.py migrate --noinput 2>&1 | Select-Object -Last 3
if ($LASTEXITCODE -eq 0) { Ok "Миграции применены" }
else { Warn "Миграции не применились (проверьте доступ к БД от владельца)." }
$env:DB_USER = $savedUser
$env:DB_PASSWORD = $savedPwd

# ---------------------------------------------------------------------------
# 6. Демонстрационные данные и администратор
# ---------------------------------------------------------------------------
Step "6/7" "Проверка данных и учётных записей"
# Файл .demo_disabled создаётся после очистки демо-данных на странице входа:
# пока он есть, автозаполнение не выполняется (в базе реальные данные).
$demoLock = Join-Path $ProjectRoot ".demo_disabled"
if (Test-Path -LiteralPath $demoLock) {
    Ok "Демо-данные отключены (.demo_disabled) - автозаполнение пропущено"
} elseif (-not $SkipDemo) {
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

# Если порт занят (например, сервер уже запущен) - берём следующий свободный
function Test-PortFree {
    param([int]$P)
    return -not (Get-NetTCPConnection -LocalPort $P -State Listen -ErrorAction SilentlyContinue)
}
$requestedPort = $Port
while (-not (Test-PortFree $Port) -and $Port -lt ($requestedPort + 10)) {
    $Port++
}
if ($Port -ne $requestedPort) {
    Warn "Порт $requestedPort занят - использую $Port"
}

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
$serverExit = $LASTEXITCODE
Remove-Job -State Completed -ErrorAction SilentlyContinue
if ($serverExit -ne 0) {
    Fail "Веб-сервер завершился с кодом $serverExit (см. сообщения выше)."
}
exit $serverExit
