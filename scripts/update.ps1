# ============================================================================
#  ОБНОВЛЕНИЕ ИС КОЛЛЕДЖА
#  Проверяет манифест обновлений, скачивает архив, проверяет контрольную сумму,
#  делает резервную копию кода и применяет обновление (код + зависимости +
#  миграции). Запускается из scripts\start.ps1 при старте системы.
#
#  Коды возврата:
#    0 - обновлений нет (или проверка отключена)
#    2 - обновление установлено
#    3 - обновление есть, но не установлено (режим -CheckOnly / UPDATE_AUTO=False)
#    4 - ошибка (не удалось проверить/скачать/применить)
# ============================================================================
param(
    [string]$ProjectRoot = "",
    [string]$Url = "",
    [switch]$CheckOnly,      # только сообщить о версии, ничего не менять
    [switch]$Force,          # установить даже если версия не новее
    [switch]$Quiet           # меньше вывода (для запуска из start.ps1)
)

$ErrorActionPreference = "Continue"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }

if (-not $ProjectRoot) {
    $ProjectRoot = Split-Path $PSScriptRoot -Parent
}
$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$LogDir = Join-Path $ProjectRoot "logs"
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$LogFile = Join-Path $LogDir "update.log"

function Log($msg) {
    try { Add-Content -LiteralPath $LogFile -Value ("{0}  {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $msg) -Encoding UTF8 } catch { }
}
function Say($msg, $color = "Gray") { if (-not $Quiet) { Write-Host "    $msg" -ForegroundColor $color } }
function Ok($msg) { Say "OK  $msg" "Green" }
function Warn($msg) { Say "!   $msg" "Yellow" }
function Fail($msg) { Say "X   $msg" "Red" }

# --- Параметры из .env -------------------------------------------------------
function Get-EnvValue($name, $default = "") {
    $envFile = Join-Path $ProjectRoot ".env"
    if (-not (Test-Path -LiteralPath $envFile)) { return $default }
    $line = Get-Content -LiteralPath $envFile -ErrorAction SilentlyContinue |
        Where-Object { $_ -match "^$name=" } | Select-Object -First 1
    if (-not $line) { return $default }
    return (($line -split '=', 2)[1]).Trim()
}

if (-not $Url) { $Url = Get-EnvValue "UPDATE_URL" "https://github.com/Ara2030/college_info_sys/releases/latest/download/version.json" }
$auto = (Get-EnvValue "UPDATE_AUTO" "True").ToLower()
$autoApply = @('1', 'true', 'yes', 'on') -contains $auto

# --- Текущая версия ----------------------------------------------------------
$versionFile = Join-Path $ProjectRoot "VERSION"
$current = "0.0.0"
if (Test-Path -LiteralPath $versionFile) {
    $current = (Get-Content -LiteralPath $versionFile -Raw -Encoding UTF8).Trim()
}
if (-not $current) { $current = "0.0.0" }

# --- Чтение манифеста --------------------------------------------------------
function Get-Manifest($address) {
    if ($address -match '^(https?)://') {
        try {
            return Invoke-RestMethod -Uri $address -TimeoutSec 10 -UseBasicParsing
        } catch {
            Log "не удалось прочитать манифест $address : $($_.Exception.Message)"
            return $null
        }
    }
    $path = $address -replace '^file:///', ''
    if (Test-Path -LiteralPath $path) {
        try { return (Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json) } catch { return $null }
    }
    return $null
}

$manifest = Get-Manifest $Url
if (-not $manifest) {
    Say "сервер обновлений недоступен - работаю на текущей версии ($current)" "DarkGray"
    exit 0
}
if (-not $manifest.version) {
    Fail "манифест обновлений некорректный (нет поля version)"
    exit 4
}

try { $remoteVersion = [version]$manifest.version } catch {
    Fail "некорректный номер версии в манифесте: $($manifest.version)"
    exit 4
}
try { $localVersion = [version]$current } catch { $localVersion = [version]"0.0.0" }

if (-not $Force -and $remoteVersion -le $localVersion) {
    Say "обновлений нет (версия $current)" "DarkGray"
    exit 0
}

Say "доступно обновление: $current -> $($manifest.version)" "Cyan"
if ($manifest.notes) { Say "что нового: $($manifest.notes)" "DarkGray" }
Log "найдено обновление $current -> $($manifest.version)"

if ($CheckOnly -or -not $autoApply) {
    if (-not $CheckOnly) { Warn "автоустановка отключена (UPDATE_AUTO=False) - обновление не установлено" }
    exit 3
}

# --- Скачивание --------------------------------------------------------------
$work = Join-Path $env:TEMP ("college_update_" + $manifest.version)
Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $work -Force | Out-Null
$zip = Join-Path $work "update.zip"

Say "скачиваю обновление..." "DarkGray"
try {
    if ($manifest.url -match '^(https?)://') {
        Invoke-WebRequest -Uri $manifest.url -OutFile $zip -TimeoutSec 600 -UseBasicParsing
    } else {
        $src = $manifest.url -replace '^file:///', ''
        if (-not (Test-Path -LiteralPath $src)) { throw "файл не найден: $src" }
        Copy-Item -LiteralPath $src -Destination $zip -Force
    }
} catch {
    Fail "не удалось скачать: $($_.Exception.Message)"
    Log "ошибка скачивания: $($_.Exception.Message)"
    exit 4
}

$sizeMb = [math]::Round((Get-Item $zip).Length / 1MB, 1)
Say "получено $sizeMb МБ" "DarkGray"

# --- Проверка контрольной суммы ---------------------------------------------
if ($manifest.sha256) {
    $actual = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToUpper()
    $expected = $manifest.sha256.ToUpper()
    if ($actual -ne $expected) {
        Fail "контрольная сумма не совпала - файл повреждён или подменён"
        Log "SHA256 не совпал: ожидался $expected, получен $actual"
        Remove-Item -LiteralPath $zip -Force -ErrorAction SilentlyContinue
        exit 4
    }
    Say "контрольная сумма верна" "DarkGray"
} else {
    Warn "в манифесте нет SHA256 - целостность не проверена"
}

# --- Резервная копия ---------------------------------------------------------
Say "делаю резервную копию кода..." "DarkGray"
$backupDir = Join-Path $ProjectRoot "backups"
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$backupZip = Join-Path $backupDir ("app-" + $current + "-" + $stamp + ".zip")
$backupSrc = Join-Path $work "backup_src"
$excludeDirs = @('.venv', '.git', 'logs', 'media', 'backups', '_install', 'dist', 'installer', '__pycache__')
$rcDirs = @("`"$ProjectRoot`"", "`"$backupSrc`"", "/E", "/NFL", "/NDL", "/NJH", "/NJS", "/R:1", "/W:1", "/XD") +
          ($excludeDirs | ForEach-Object { "$ProjectRoot\$_" })
$rcDirs += @("/XF", "$ProjectRoot\.env")
& robocopy @rcDirs | Out-Null
if ($LASTEXITCODE -ge 8) {
    Warn "не удалось сделать резервную копию - обновление отменено"
    Log "резервная копия не создана (robocopy $LASTEXITCODE)"
    exit 4
}
try {
    Compress-Archive -Path (Join-Path $backupSrc "*") -DestinationPath $backupZip -Force
    Say "копия: backups\$([System.IO.Path]::GetFileName($backupZip))" "DarkGray"
} catch {
    Warn "архив резервной копии не создан: $($_.Exception.Message)"
}

# --- Применение --------------------------------------------------------------
$reqBefore = ""
$reqPath = Join-Path $ProjectRoot "requirements.txt"
if (Test-Path -LiteralPath $reqPath) { $reqBefore = (Get-FileHash -LiteralPath $reqPath).Hash }

$srcDir = Join-Path $work "src"
try {
    Expand-Archive -LiteralPath $zip -DestinationPath $srcDir -Force
} catch {
    Fail "архив повреждён: $($_.Exception.Message)"
    exit 4
}

Say "применяю файлы..." "DarkGray"
$copy = @("`"$srcDir`"", "`"$ProjectRoot`"", "/E", "/NFL", "/NDL", "/NJH", "/NJS", "/R:1", "/W:1",
          "/XD", ".venv", "logs", "media", "backups", "_install",
          "/XF", ".env")
& robocopy @copy | Out-Null
if ($LASTEXITCODE -ge 8) {
    Fail "не удалось скопировать файлы обновления"
    Log "robocopy при копировании обновления: $LASTEXITCODE"
    exit 4
}

$venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$reqAfter = ""
if (Test-Path -LiteralPath $reqPath) { $reqAfter = (Get-FileHash -LiteralPath $reqPath).Hash }

if ($reqBefore -ne $reqAfter -and (Test-Path -LiteralPath $venvPython)) {
    Say "обновились зависимости - устанавливаю библиотеки..." "DarkGray"
    $pipArgs = @("-m", "pip", "install", "--quiet", "--disable-pip-version-check", "-r", $reqPath)
    $wheels = Join-Path $ProjectRoot "_install\wheels"
    if (Test-Path -LiteralPath $wheels) { $pipArgs += @("--no-index", "--find-links", $wheels) }
    Push-Location $ProjectRoot
    & $venvPython @pipArgs
    $pipCode = $LASTEXITCODE
    Pop-Location
    if ($pipCode -ne 0) {
        Fail "библиотеки не установились - откатитесь к backups\$([System.IO.Path]::GetFileName($backupZip))"
        Log "pip install при обновлении завершился с кодом $pipCode"
        exit 4
    }
    Ok "библиотеки обновлены"
}

# Миграции (от владельца БД)
if (Test-Path -LiteralPath $venvPython) {
    $adminUser = Get-EnvValue "DB_ADMIN_USER" "postgres"
    $adminPwd = Get-EnvValue "DB_ADMIN_PASSWORD" ""
    $savedUser = $env:DB_USER
    $savedPwd = $env:DB_PASSWORD
    $env:DB_USER = $adminUser
    $env:DB_PASSWORD = $adminPwd
    Push-Location $ProjectRoot
    Say "применяю миграции..." "DarkGray"
    & $venvPython manage.py migrate --noinput 2>&1 | Select-Object -Last 2 | ForEach-Object { Say $_ "DarkGray" }
    $migCode = $LASTEXITCODE
    Pop-Location
    $env:DB_USER = $savedUser
    $env:DB_PASSWORD = $savedPwd
    if ($migCode -ne 0) {
        Fail "миграции не применились - откатитесь к backups\$([System.IO.Path]::GetFileName($backupZip))"
        Log "migrate при обновлении завершился с кодом $migCode"
        exit 4
    }
}

# --- Фиксация версии ---------------------------------------------------------
$applied = if ($manifest.version) { $manifest.version } else { $current }
[System.IO.File]::WriteAllText($versionFile, "$applied`r`n", (New-Object System.Text.UTF8Encoding($false)))
Log "обновление установлено: $current -> $applied"
Ok "обновлено до версии $applied"

Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue

# Чистим старые резервные копии (оставляем 5 последних)
try {
    Get-ChildItem $backupDir -Filter "app-*.zip" | Sort-Object LastWriteTime -Descending |
        Select-Object -Skip 5 | Remove-Item -Force -ErrorAction SilentlyContinue
} catch { }

exit 2
