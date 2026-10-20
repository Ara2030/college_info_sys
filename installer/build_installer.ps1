# ============================================================================
#  Сборка установщика ИС колледжа
#  Готовит payload (код, дамп БД, библиотеки, дистрибутивы) и компилирует .exe
#  Запуск: powershell -ExecutionPolicy Bypass -File installer\build_installer.ps1
# ============================================================================
param(
    [switch]$SkipDump,        # не делать свежий дамп базы
    [switch]$SkipWheels       # не обновлять набор библиотек
)

$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
$root = Split-Path $here -Parent
$payload = Join-Path $here "payload"
$cache = Join-Path $here "cache"

function Step($t) { Write-Host "`n== $t" -ForegroundColor Cyan }
function Ok($t) { Write-Host "   OK  $t" -ForegroundColor Green }

foreach ($d in @("app", "db", "wheels", "deps", "sql")) {
    New-Item -ItemType Directory -Path (Join-Path $payload $d) -Force | Out-Null
}
New-Item -ItemType Directory -Path $cache -Force | Out-Null

# ---------------------------------------------------------------------------
Step "1. Код проекта -> payload\app"
# ---------------------------------------------------------------------------
$excludeDirs = @(".venv", ".git", ".gigacode", "dist", "logs", "__pycache__", "installer", ".pytest_cache")
$rcArgs = @("`"$root`"", "`"$payload\app`"", "/E", "/NFL", "/NDL", "/NJH", "/NJS", "/R:1", "/W:1", "/PURGE", "/XD")
$rcArgs += ($excludeDirs | ForEach-Object { "`"$root\$_`"" })
$rcArgs += @("/XF", "`"$root\.env`"")
& robocopy @rcArgs | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy завершился с кодом $LASTEXITCODE" }
Ok ("код скопирован, {0:N1} МБ" -f ((Get-ChildItem "$payload\app" -Recurse -File | Measure-Object Length -Sum).Sum / 1MB))

# ---------------------------------------------------------------------------
Step "2. Дамп базы данных"
# ---------------------------------------------------------------------------
if ($SkipDump) {
    Ok "пропущено (-SkipDump)"
} else {
    $pgDump = $null
    $svc = Get-CimInstance Win32_Service -Filter "Name LIKE 'postgresql%'" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($svc -and $svc.PathName) {
        $m = [regex]::Match($svc.PathName, '"([^"]*bin)[\\/][^\\/"]+"')
        if ($m.Success) { $pgDump = Join-Path $m.Groups[1].Value "pg_dump.exe" }
    }
    if (-not $pgDump -or -not (Test-Path $pgDump)) {
        $pgDump = Get-ChildItem "C:\Program Files\PostgreSQL\*\bin\pg_dump.exe" -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending | Select-Object -First 1 -ExpandProperty FullName
    }
    if (-not $pgDump) { throw "pg_dump.exe не найден" }

    $env:PGPASSWORD = ""
    & $pgDump -h 127.0.0.1 -U postgres --no-owner --no-privileges --encoding=UTF8 -d college_sys -f "$payload\db\college_sys.sql"
    if ($LASTEXITCODE -ne 0) { throw "pg_dump завершился с ошибкой $LASTEXITCODE" }
    Ok ("дамп готов, {0:N1} МБ" -f ((Get-Item "$payload\db\college_sys.sql").Length / 1MB))
}

# ---------------------------------------------------------------------------
Step "3. Библиотеки Python (для офлайн-установки)"
# ---------------------------------------------------------------------------
if ($SkipWheels) {
    Ok "пропущено (-SkipWheels)"
} else {
    $py = Join-Path $root ".venv\Scripts\python.exe"
    if (-not (Test-Path $py)) { throw "Не найден .venv проекта: запустите start.bat один раз" }
    Get-ChildItem "$payload\wheels\*.whl" -ErrorAction SilentlyContinue | Remove-Item -Force
    & $py -m pip download -r (Join-Path $root "requirements.txt") -d "$payload\wheels" --only-binary=:all: --quiet
    if ($LASTEXITCODE -ne 0) { throw "pip download завершился с ошибкой" }
    Ok ("колёс: {0}" -f (Get-ChildItem "$payload\wheels" | Measure-Object).Count)
}

# ---------------------------------------------------------------------------
Step "4. Дистрибутивы Python и PostgreSQL"
# ---------------------------------------------------------------------------
$pythonInstaller = "python-3.14.7-amd64.exe"
$pgInstaller = "postgresql-17.11-1-windows-x64.exe"
$deps = @(
    @{ Name = $pythonInstaller; Url = "https://www.python.org/ftp/python/3.14.7/$pythonInstaller" },
    @{ Name = $pgInstaller; Url = "https://get.enterprisedb.com/postgresql/$pgInstaller" }
)
foreach ($d in $deps) {
    $target = Join-Path $payload "deps\$($d.Name)"
    if (Test-Path $target) { Ok "$($d.Name) уже в комплекте"; continue }

    $cached = Join-Path $cache $d.Name
    if (-not (Test-Path $cached)) {
        Write-Host "   Скачиваю $($d.Name)..." -ForegroundColor Yellow
        curl.exe -sL --retry 3 -o $cached $d.Url
        if ($LASTEXITCODE -ne 0) { throw "Не удалось скачать $($d.Url)" }
    }
    Copy-Item $cached $target -Force
    Ok ("{0}, {1:N1} МБ" -f $d.Name, ((Get-Item $target).Length / 1MB))
}

# ---------------------------------------------------------------------------
Step "5. Компиляция установщика"
# ---------------------------------------------------------------------------
$iscc = @(
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe",
    (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe")
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { throw "Inno Setup не найден. Установите: winget install JRSoftware.InnoSetup" }

& $iscc (Join-Path $here "college_is.iss")
if ($LASTEXITCODE -ne 0) { throw "Компиляция установщика завершилась с ошибкой" }

$setup = Get-ChildItem (Join-Path $root "dist\installer\CollegeIS_Setup_*.exe") |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
Ok ("Готово: $($setup.FullName) ({0:N0} МБ)" -f ($setup.Length / 1MB))
