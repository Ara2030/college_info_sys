# ============================================================================
#  ИНФОРМАЦИОННАЯ СИСТЕМА КОЛЛЕДЖА (СПО) - установка зависимостей и базы
#  Запускается установщиком (Setup.exe) с правами администратора.
#  Проверяет Python и PostgreSQL, ставит их при необходимости, создаёт роль
#  приложения и базу данных, разворачивает дамп, собирает виртуальное окружение.
# ============================================================================
param(
    [Parameter(Mandatory = $false)][string]$InstallDir = "",
    [string]$DbName = "college_sys",
    [int]$PgPort = 5432,
    [string]$PgAdminPassword = "",      # пароль суперпользователя postgres (пусто = сгенерировать)
    [switch]$SkipPython,                # не устанавливать Python
    [switch]$SkipPostgres,              # не устанавливать PostgreSQL
    [switch]$KeepInstallers,            # не удалять дистрибутивы после установки
[switch]$NoCleanup,                  # алиас для -KeepInstallers
    [string]$AppRole = 'college_app'       # роль БД приложения (для тестовых установок)
)

$ErrorActionPreference = "Continue"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }

if (-not $InstallDir) { $InstallDir = Split-Path $PSScriptRoot -Parent }
if (-not (Test-Path -LiteralPath $InstallDir)) {
    Write-Host "Папка установки не найдена: $InstallDir" -ForegroundColor Red
    exit 1
}
$InstallDir = (Resolve-Path -LiteralPath $InstallDir).Path
$PayloadDir = Join-Path $InstallDir "_install"
$LogDir = Join-Path $InstallDir "logs"

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$LogFile = Join-Path $LogDir "install.log"
try { Start-Transcript -Path $LogFile -Force | Out-Null } catch { }

function Log($msg, $color = "Gray") {
    Write-Host $msg -ForegroundColor $color
}
function Step($n, $text) { Log "" ; Log "[$n] $text" "Cyan" }
function Ok($text) { Log "    OK  $text" "Green" }
function Warn($text) { Log "    !   $text" "Yellow" }
function Fail($text) { Log "    X   $text" "Red" }
function Die($text) {
    Fail $text
    Log ""
    Log "Установка прервана. Подробный журнал: $LogFile" "Red"
    try { Stop-Transcript | Out-Null } catch { }
    exit 1
}

function New-RandomString {
    param([int]$Length = 20, [string]$Chars = "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789")
    $bytes = New-Object byte[] $Length
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $rng.GetBytes($bytes)
    $sb = New-Object System.Text.StringBuilder
    foreach ($b in $bytes) { [void]$sb.Append($Chars[$b % $Chars.Length]) }
    return $sb.ToString()
}

function Test-PythonWorks {
    param([string]$Path)
    if (-not $Path -or -not (Test-Path -LiteralPath $Path)) { return $false }
    try {
        $out = & $Path -c "import sys; print('py-ok')" 2>&1
        return ($LASTEXITCODE -eq 0 -and ("$out" -match 'py-ok'))
    } catch { return $false }
}

function Find-BasePython {
    $found = @()
    $patterns = @(
        "C:\Program Files\Python3*\python.exe",
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python3*\python.exe"),
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
        try { $v = & $exe.FullName -c "import sys; print(sys.version_info[0]*100+sys.version_info[1])" 2>$null } catch { continue }
        if ($v -and [int]$v -ge 310) { return $exe.FullName }
    }
    return $null
}

function Find-PgBin {
    $candidates = @()
    $svc = Get-CimInstance Win32_Service -Filter "Name LIKE 'postgresql%'" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($svc -and $svc.PathName) {
        $m = [regex]::Match($svc.PathName, '"([^"]*bin)[\\/][^\\/"]+"')
        if ($m.Success) { $candidates += $m.Groups[1].Value }
    }
    $candidates += (Get-ChildItem "C:\Program Files\PostgreSQL\*\bin" -Directory -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending | Select-Object -ExpandProperty FullName)
    foreach ($c in $candidates) {
        if (Test-Path -LiteralPath (Join-Path $c "psql.exe")) { return $c }
    }
    return $null
}

Write-Host "============================================================" -ForegroundColor White
Write-Host "   ИНФОРМАЦИОННАЯ СИСТЕМА КОЛЛЕДЖА - УСТАНОВКА" -ForegroundColor White
Write-Host "============================================================" -ForegroundColor White
Log "Папка установки: $InstallDir"
Log "База данных: $DbName, порт PostgreSQL: $PgPort"

$report = [ordered]@{}

# ---------------------------------------------------------------------------
# 1. Python
# ---------------------------------------------------------------------------
Step "1/7" "Python"
$basePython = $null
if (-not $SkipPython) { $basePython = Find-BasePython }

if ($basePython) {
    $pv = & $basePython -c "import sys; print('.'.join(map(str, sys.version_info[:3])))" 2>$null
    Ok "Python найден: $basePython ($pv)"
    $report["Python"] = "уже установлен ($pv)"
} else {
    $pyInstaller = Get-ChildItem (Join-Path $PayloadDir "deps\python-*-amd64.exe") -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $pyInstaller) { Die "Python не найден, а дистрибутив отсутствует в комплекте." }

    Warn "Python не найден - устанавливаю ($($pyInstaller.Name))..."
    $proc = Start-Process -FilePath $pyInstaller.FullName -Wait -PassThru -ArgumentList @(
        "/quiet", "InstallAllUsers=1", "PrependPath=1", "Include_pip=1",
        "Include_test=0", "Include_launcher=1", "AssociateFiles=0"
    )
    if ($proc.ExitCode -ne 0) { Die "Установщик Python завершился с кодом $($proc.ExitCode)." }

    Start-Sleep -Seconds 3
    $basePython = Find-BasePython
    if (-not $basePython) { Die "Python установлен, но не найден. Перезагрузите компьютер и запустите установку снова." }
    Ok "Python установлен: $basePython"
    $report["Python"] = "установлен заново"
}

# ---------------------------------------------------------------------------
# 2. PostgreSQL
# ---------------------------------------------------------------------------
Step "2/7" "PostgreSQL"
$pgBin = Find-PgBin
$pgInstalled = $false

if ($SkipPostgres) {
    if ($pgBin) { Ok "PostgreSQL: используется существующий ($pgBin)"; $pgInstalled = $true }
    else { Warn "PostgreSQL не найден (проверка отключена флагом)" }
} elseif ($pgBin) {
    Ok "PostgreSQL уже установлен ($pgBin)"
    $pgInstalled = $true
    $report["PostgreSQL"] = "уже установлен"
}

if (-not $pgInstalled) {
    $pgInstaller = Get-ChildItem (Join-Path $PayloadDir "deps\postgresql-*-windows-x64.exe") -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $pgInstaller) { Die "PostgreSQL не найден, а дистрибутив отсутствует в комплекте." }

    if (-not $PgAdminPassword) { $PgAdminPassword = New-RandomString -Length 24 }
    Warn "PostgreSQL не найден - устанавливаю ($($pgInstaller.Name))... Это может занять несколько минут."
    $pgArgs = @(
        "--mode", "unattended",
        "--unattendedmodeui", "minimal",
        "--superpassword", $PgAdminPassword,
        "--servicename", "postgresql-x64-17",
        "--serverport", "$PgPort",
        "--enable-components", "server,commandlinetools"
    )
    $proc = Start-Process -FilePath $pgInstaller.FullName -Wait -PassThru -ArgumentList $pgArgs
    if ($proc.ExitCode -ne 0) { Die "Установщик PostgreSQL завершился с кодом $($proc.ExitCode)." }

    Start-Sleep -Seconds 5
    $pgBin = Find-PgBin
    if (-not $pgBin) { Die "PostgreSQL установлен, но psql.exe не найден." }
    Ok "PostgreSQL установлен: $pgBin"
    $report["PostgreSQL"] = "установлен заново"
}

# Ждём готовности сервера
$isReady = Join-Path $pgBin "pg_isready.exe"
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    if (Test-Path -LiteralPath $isReady) {
        & $isReady -h 127.0.0.1 -p $PgPort *> $null
        if ($LASTEXITCODE -eq 0) { $ready = $true; break }
    } else { $ready = $true; break }
    Start-Sleep -Seconds 2
}
if (-not $ready) { Die "Сервер PostgreSQL не отвечает на порту $PgPort. Проверьте службу postgresql-x64-17." }
Ok "Сервер PostgreSQL отвечает на порту $PgPort"

$psql = Join-Path $pgBin "psql.exe"
$pgDump = Join-Path $pgBin "pg_dump.exe"
$createdb = Join-Path $pgBin "createdb.exe"

# Подбор пароля администратора: сначала переданный, затем пустой (доверенная аутентификация)
if (-not $PgAdminPassword) { $PgAdminPassword = "postgres" }
$adminPwd = $null
foreach ($candidate in @($PgAdminPassword, "")) {
    $env:PGPASSWORD = $candidate
    & $psql -h 127.0.0.1 -p $PgPort -U postgres -d postgres -t -c "select 1" *> $null
    if ($LASTEXITCODE -eq 0) { $adminPwd = $candidate; break }
}
if ($null -eq $adminPwd) {
    Die "Не удалось подключиться к PostgreSQL как postgres. Укажите пароль параметром -PgAdminPassword."
}
$env:PGPASSWORD = $adminPwd
Ok "Подключение к PostgreSQL от postgres установлено"

# ---------------------------------------------------------------------------
# 3. Виртуальное окружение и зависимости (офлайн, из комплекта)
# ---------------------------------------------------------------------------
Step "3/7" "Виртуальное окружение и библиотеки"
$venvDir = Join-Path $InstallDir ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"

if (Test-PythonWorks $venvPython) {
    Ok "Виртуальное окружение уже создано"
} else {
    if (Test-Path -LiteralPath $venvDir) { Remove-Item -LiteralPath $venvDir -Recurse -Force -ErrorAction SilentlyContinue }
    Warn "Создаю виртуальное окружение..."
    & $basePython -m venv $venvDir
    if (-not (Test-PythonWorks $venvPython)) { Die "Не удалось создать виртуальное окружение." }
    Ok "Виртуальное окружение создано"
}

$wheels = Join-Path $PayloadDir "wheels"
$pipArgs = @("-m", "pip", "install", "--quiet", "--disable-pip-version-check", "-r", (Join-Path $InstallDir "requirements.txt"))
if (Test-Path -LiteralPath $wheels) {
    $pipArgs += @("--no-index", "--find-links", $wheels)
    Ok "Зависимости ставятся из локального комплекта (интернет не нужен)"
}
& $venvPython @pipArgs
if ($LASTEXITCODE -ne 0) { Die "Не удалось установить библиотеки Python." }

& $venvPython -c "import django, psycopg, openpyxl, reportlab, lxml, PIL" *> $null
if ($LASTEXITCODE -ne 0) { Die "Библиотеки установлены не полностью." }
Ok "Библиотеки установлены"

# ---------------------------------------------------------------------------
# 4. Файл параметров .env
# ---------------------------------------------------------------------------
Step "4/7" "Параметры системы (.env)"
$envFile = Join-Path $InstallDir ".env"
$appPassword = New-RandomString -Length 20
$secretKey = (& $venvPython -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())" 2>$null | Select-Object -Last 1).Trim()
if (-not $secretKey) { $secretKey = New-RandomString -Length 50 }

$envLines = @(
    "# College IS - environment (created by installer)",
    "DJANGO_DEBUG=True",
    "DJANGO_SECRET_KEY=$secretKey",
    "DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost",
    "",
    "DB_NAME=$DbName",
    "DB_USER=$AppRole",
    "DB_PASSWORD=$appPassword",
    "DB_HOST=127.0.0.1",
    "DB_PORT=$PgPort",
    "DB_ADMIN_USER=postgres",
    "DB_ADMIN_PASSWORD=$adminPwd",
    "",
    "SECURE_SSL_REDIRECT=False",
    "MASK_SENSITIVE_DATA=True"
)
[System.IO.File]::WriteAllText($envFile, ($envLines -join "`r`n") + "`r`n", (New-Object System.Text.UTF8Encoding($false)))
if (-not (Test-Path -LiteralPath $envFile)) { Die "Не удалось создать .env" }
Ok "Параметры записаны в .env (пароль БД сгенерирован)"

# ---------------------------------------------------------------------------
# 5. Роль приложения и база данных
# ---------------------------------------------------------------------------
Step "5/7" "Роль приложения и база данных"

function Invoke-Sql {
    param([string]$Database, [string]$Sql, [string]$File = "")
    if ($File) {
        & $psql -h 127.0.0.1 -p $PgPort -U postgres -d $Database -v ON_ERROR_STOP=1 -q -f $File 2>&1 | ForEach-Object { Log "      $_" "DarkGray" }
    } else {
        & $psql -h 127.0.0.1 -p $PgPort -U postgres -d $Database -v ON_ERROR_STOP=1 -q -c $Sql 2>&1 | ForEach-Object { Log "      $_" "DarkGray" }
    }
    return $LASTEXITCODE
}

$roleSql = @"
DO `$`$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$AppRole') THEN
    CREATE ROLE $AppRole LOGIN;
  END IF;
END `$`$;
ALTER ROLE $AppRole WITH LOGIN PASSWORD '$appPassword';
"@
if ((Invoke-Sql -Database "postgres" -Sql $roleSql) -ne 0) { Die "Не удалось создать роль $AppRole." }
Ok "Роль $AppRole готова (без прав суперпользователя)"

$dbExists = (& $psql -h 127.0.0.1 -p $PgPort -U postgres -d postgres -t -A -c "select 1 from pg_database where datname='$DbName'" 2>$null) -join ""
if ($dbExists -notmatch "1") {
    & $createdb -h 127.0.0.1 -p $PgPort -U postgres -E UTF8 -T template0 "$DbName" 2>&1 | ForEach-Object { Log "      $_" "DarkGray" }
    if ($LASTEXITCODE -ne 0) { Die "Не удалось создать базу $DbName." }
    Ok "База данных $DbName создана"
} else {
    Ok "База данных $DbName уже существует"
}

$tableCount = (& $psql -h 127.0.0.1 -p $PgPort -U postgres -d $DbName -t -A -c "select count(*) from pg_tables where schemaname='public'" 2>$null) -join ""
$dumpFile = Join-Path $PayloadDir "db\college_sys.sql"
if ($tableCount -match "^\d+$" -and [int]$tableCount -gt 0) {
    Warn "В базе уже есть $tableCount таблиц - данные не перезаписываю"
} elseif (Test-Path -LiteralPath $dumpFile) {
    Warn "Разворачиваю базу из дампа..."
    if ((Invoke-Sql -Database $DbName -File $dumpFile) -ne 0) { Die "Ошибка восстановления дампа базы." }
    $students = (& $psql -h 127.0.0.1 -p $PgPort -U postgres -d $DbName -t -A -c "select count(*) from contingent_student" 2>$null) -join ""
    Ok "База восстановлена (студентов: $students)"
} else {
    Warn "Дамп не найден - база будет создана миграциями"
}

$grantSql = @"
GRANT CONNECT ON DATABASE $DbName TO $AppRole;
GRANT USAGE ON SCHEMA public TO $AppRole;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO $AppRole;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO $AppRole;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO $AppRole;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO $AppRole;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO $AppRole;
REVOKE CREATE ON SCHEMA public FROM $AppRole;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
"@
if ((Invoke-Sql -Database $DbName -Sql $grantSql) -ne 0) { Die "Не удалось выдать права роли $AppRole." }
Ok "Права роли $AppRole выданы (CRUD без DDL)"

# ---------------------------------------------------------------------------
# 6. Миграции и проверка системы
# ---------------------------------------------------------------------------
Step "6/7" "Миграции и проверка"
$env:DB_USER = "postgres"
$env:DB_PASSWORD = $adminPwd
Push-Location $InstallDir
& $venvPython manage.py migrate --noinput 2>&1 | Select-Object -Last 3 | ForEach-Object { Log "      $_" "DarkGray" }
if ($LASTEXITCODE -ne 0) { Pop-Location; Die "Ошибка применения миграций." }
Ok "Миграции применены"

& $venvPython manage.py check 2>&1 | Select-Object -Last 2 | ForEach-Object { Log "      $_" "DarkGray" }
if ($LASTEXITCODE -ne 0) { Pop-Location; Die "Проверка Django выявила ошибки." }

# Проверяем, что приложение реально работает под ролью приложения
$env:DB_USER = $AppRole
$env:DB_PASSWORD = $appPassword
$checkOut = & $venvPython -c @"
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
django.setup()
from contingent.models import Student
from django.contrib.auth.models import User
print('students=%d users=%d' % (Student.objects.count(), User.objects.count()))
"@ 2>&1
Pop-Location
if ($LASTEXITCODE -ne 0) { Die "Приложение не подключается к базе под ролью ${AppRole}:`n$checkOut" }
Ok "Приложение подключается к базе под ролью $AppRole ($checkOut)"
$report["База данных"] = ($checkOut -join " ")

# ---------------------------------------------------------------------------
# 7. Итог
# ---------------------------------------------------------------------------
Step "7/7" "Завершение"
$report["Пароль postgres"] = $adminPwd
$report["Пароль роли приложения"] = $appPassword

$infoFile = Join-Path $LogDir "ДОСТУПЫ.txt"
$info = @(
    "ИНФОРМАЦИОННАЯ СИСТЕМА КОЛЛЕДЖА - учётные данные",
    "Установлена: $(Get-Date -Format 'dd.MM.yyyy HH:mm')",
    "Папка: $InstallDir",
    "",
    "Вход в систему: admin / admin123   (сменить после установки!)",
    "Демо-роли (только при DEBUG=True): director/director123, methodist/methodist123,",
    "  teacher1/teacher123, student1/student123, parent1/parent123",
    "",
    "База данных: $DbName на 127.0.0.1:$PgPort",
    "  суперпользователь postgres: пароль $adminPwd",
    "  роль приложения ${AppRole}: пароль $appPassword",
    "",
    "Файл параметров: $envFile",
    "Журнал установки: $LogFile"
)
[System.IO.File]::WriteAllText($infoFile, ($info -join "`r`n") + "`r`n", (New-Object System.Text.UTF8Encoding($false)))
Ok "Данные доступа сохранены: $infoFile"

if (-not $KeepInstallers -and -not $NoCleanup) {
    $deps = Join-Path $PayloadDir "deps"
    if (Test-Path -LiteralPath $deps) {
        Remove-Item -LiteralPath $deps -Recurse -Force -ErrorAction SilentlyContinue
        Ok "Дистрибутивы удалены (освобождено место); библиотеки оставлены для починки"
    }
}

Log ""
Log "============================================================" "Green"
Log "   УСТАНОВКА ЗАВЕРШЕНА УСПЕШНО" "Green"
Log "   Запуск: ярлык «ИС колледжа» на рабочем столе или start.bat" "White"
Log "============================================================" "Green"

try { Stop-Transcript | Out-Null } catch { }
exit 0
