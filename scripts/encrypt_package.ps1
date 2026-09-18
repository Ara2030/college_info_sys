# ============================================================================
#  ШИФРОВАНИЕ ПАКЕТА ИС КОЛЛЕДЖА (AES-256)
#  Защищает дамп БД и архив проекта паролем перед передачей.
#  Запуск: powershell -ExecutionPolicy Bypass -File scripts\encrypt_package.ps1
# ============================================================================
param(
    [string]$Path = "",             # файл или папка для шифрования (по умолчанию - dist)
    [string]$OutputFile = "",       # имя зашифрованного файла
    [string]$Password = "",         # пароль (если пусто - сгенерируется надёжный)
    [int]$Iterations = 200000       # число итераций PBKDF2
)

$ErrorActionPreference = "Stop"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }
$ProjectRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $ProjectRoot

function Step($t) { Write-Host "`n>> $t" -ForegroundColor Cyan }
function Ok($t)   { Write-Host "   OK  $t" -ForegroundColor Green }
function Warn($t) { Write-Host "   !   $t" -ForegroundColor Yellow }

Write-Host "============================================================" -ForegroundColor White
Write-Host "   ШИФРОВАНИЕ ПАКЕТА (AES-256)" -ForegroundColor White
Write-Host "============================================================" -ForegroundColor White

# ---------------------------------------------------------------------------
# 1. Определяем источник
# ---------------------------------------------------------------------------
Step "1/4 Подготовка данных"
if (-not $Path) {
    $dist = Join-Path $ProjectRoot "dist"
    if (Test-Path -LiteralPath $dist) { $Path = $dist }
    else { $Path = $ProjectRoot }
}
if (-not (Test-Path -LiteralPath $Path)) {
    Write-Host "   X   Путь не найден: $Path" -ForegroundColor Red
    Read-Host "Нажмите Enter для выхода"; exit 1
}

$isDir = (Get-Item -LiteralPath $Path).PSIsContainer
$tempZip = $null

if ($isDir) {
    # Пакуем папку в ZIP (во временный файл)
    $tempZip = Join-Path $env:TEMP ("ahe_pack_" + [guid]::NewGuid().ToString('N') + ".zip")
    Write-Host "   Упаковка папки: $Path" -ForegroundColor Gray
    Compress-Archive -Path (Join-Path $Path "*") -DestinationPath $tempZip -CompressionLevel Optimal
    $sourceFile = $tempZip
    Ok "Временный архив: $([math]::Round((Get-Item $tempZip).Length/1KB,1)) КБ"
} else {
    $sourceFile = (Resolve-Path -LiteralPath $Path).Path
    Ok "Файл для шифрования: $(Split-Path $sourceFile -Leaf)"
}

# ---------------------------------------------------------------------------
# 2. Пароль
# ---------------------------------------------------------------------------
Step "2/4 Пароль шифрования"
$generated = $false
if (-not $Password) {
    # Генерация надёжного пароля (24 символа, без неоднозначных)
    $chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%&*'
    $rnd = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $bytes = New-Object byte[] 24
    $rnd.GetBytes($bytes)
    $Password = -join ($bytes | ForEach-Object { $chars[$_ % $chars.Length] })
    $generated = $true
    Ok "Сгенерирован надёжный пароль (сохраните его!)"
} else {
    Ok "Используется указанный пароль"
}
if ($Password.Length -lt 8) {
    Warn "Пароль короче 8 символов - надёжность снижена"
}

# ---------------------------------------------------------------------------
# 3. Шифрование AES-256
# ---------------------------------------------------------------------------
Step "3/4 Шифрование (AES-256-CBC + PBKDF2)"
if (-not $OutputFile) {
    $base = if ($isDir) { Split-Path $Path -Leaf } else { [IO.Path]::GetFileNameWithoutExtension($sourceFile) }
    $OutputFile = Join-Path $ProjectRoot "dist\$base`_encrypted.ahe"
}
$outDir = Split-Path $OutputFile -Parent
if (-not (Test-Path -LiteralPath $outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }

# Соль и вектор инициализации
$salt = New-Object byte[] 16
$iv = New-Object byte[] 16
$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$rng.GetBytes($salt)
$rng.GetBytes($iv)

# Ключ из пароля (PBKDF2, SHA-256)
$kdf = New-Object System.Security.Cryptography.Rfc2898DeriveBytes(
    $Password, $salt, $Iterations, [System.Security.Cryptography.HashAlgorithmName]::SHA256)
$key = $kdf.GetBytes(32)   # 256 бит

$aes = [System.Security.Cryptography.Aes]::Create()
$aes.KeySize = 256
$aes.Key = $key
$aes.IV = $iv
$aes.Mode = [System.Security.Cryptography.CipherMode]::CBC
$aes.Padding = [System.Security.Cryptography.PaddingMode]::PKCS7
$encryptor = $aes.CreateEncryptor()

# Пишем: магия (4) + соль (16) + IV (16) + шифротекст
$inStream = [System.IO.File]::OpenRead($sourceFile)
$outStream = [System.IO.File]::Create($OutputFile)
try {
    $magic = [System.Text.Encoding]::ASCII.GetBytes('AHE1')
    $outStream.Write($magic, 0, $magic.Length)
    $outStream.Write($salt, 0, $salt.Length)
    $outStream.Write($iv, 0, $iv.Length)

    $crypto = New-Object System.Security.Cryptography.CryptoStream(
        $outStream, $encryptor, [System.Security.Cryptography.CryptoStreamMode]::Write)
    $buffer = New-Object byte[] 81920
    while (($read = $inStream.Read($buffer, 0, $buffer.Length)) -gt 0) {
        $crypto.Write($buffer, 0, $read)
    }
    $crypto.FlushFinalBlock()
    $crypto.Dispose()
} finally {
    $inStream.Dispose()
    $outStream.Dispose()
    $aes.Dispose()
    $kdf.Dispose()
}

$outSize = [math]::Round((Get-Item -LiteralPath $OutputFile).Length / 1KB, 1)
Ok "Зашифрованный файл: $(Split-Path $OutputFile -Leaf) ($outSize КБ)"

# Удаляем временный ZIP (в нём были данные без шифрования)
if ($tempZip -and (Test-Path -LiteralPath $tempZip)) {
    Remove-Item -LiteralPath $tempZip -Force
    Ok "Временный незашифрованный архив удалён"
}

# ---------------------------------------------------------------------------
# 4. Контрольная сумма и инструкция
# ---------------------------------------------------------------------------
Step "4/4 Контроль целостности"
$hash = (Get-FileHash -LiteralPath $OutputFile -Algorithm SHA256).Hash
Ok "SHA-256: $($hash.Substring(0,32))..."

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "   ШИФРОВАНИЕ ЗАВЕРШЕНО (AES-256)" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "   Файл для передачи: $OutputFile" -ForegroundColor White
Write-Host "   SHA-256: $hash" -ForegroundColor Gray
Write-Host ""

if ($generated) {
    Write-Host "   ПАРОЛЬ (передайте отдельным каналом!):" -ForegroundColor Yellow
    Write-Host "   $Password" -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "   ИНСТРУКЦИЯ ДЛЯ ПОЛУЧАТЕЛЯ" -ForegroundColor Cyan
Write-Host "   1. Сохранить файл *.ahe в папке проекта (рядом со scripts\)" -ForegroundColor Gray
Write-Host "   2. Выполнить:" -ForegroundColor Gray
Write-Host "      powershell -ExecutionPolicy Bypass -File scripts\decrypt_package.ps1 -File <файл.ahe>" -ForegroundColor White
Write-Host "   3. Ввести пароль (запросится)" -ForegroundColor Gray
Write-Host "   4. Распаковать полученный ZIP и запустить start.bat" -ForegroundColor Gray
Write-Host ""
Write-Host "   ВАЖНО: пароль передавайте ДРУГИМ каналом (не вместе с файлом)!" -ForegroundColor Yellow
Write-Host ""
