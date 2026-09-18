# ============================================================================
#  РАСШИФРОВКА ПАКЕТА ИС КОЛЛЕДЖА (AES-256)
#  Восстанавливает данные, зашифрованные scripts\encrypt_package.ps1
#  Запуск: powershell -ExecutionPolicy Bypass -File scripts\decrypt_package.ps1 -File <файл.ahe>
# ============================================================================
param(
    [string]$File = "",             # зашифрованный файл *.ahe
    [string]$Password = "",         # пароль (если пусто - запросит интерактивно)
    [string]$OutputPath = "",       # куда сохранить (по умолчанию - рядом)
    [switch]$Extract                # распаковать полученный ZIP автоматически
)

$ErrorActionPreference = "Stop"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }
$ProjectRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $ProjectRoot

function Step($t) { Write-Host "`n>> $t" -ForegroundColor Cyan }
function Ok($t)   { Write-Host "   OK  $t" -ForegroundColor Green }
function Fail($t) { Write-Host "   X   $t" -ForegroundColor Red }

Write-Host "============================================================" -ForegroundColor White
Write-Host "   РАСШИФРОВКА ПАКЕТА (AES-256)" -ForegroundColor White
Write-Host "============================================================" -ForegroundColor White

# ---------------------------------------------------------------------------
# 1. Поиск файла
# ---------------------------------------------------------------------------
Step "1/4 Поиск зашифрованного файла"
if (-not $File) {
    $found = Get-ChildItem -LiteralPath $ProjectRoot -Recurse -Filter "*.ahe" -ErrorAction SilentlyContinue |
             Select-Object -First 1
    if ($found) { $File = $found.FullName }
}
if (-not $File -or -not (Test-Path -LiteralPath $File)) {
    Fail "Файл *.ahe не найден. Укажите путь: -File C:\path\package.ahe"
    Read-Host "Нажмите Enter для выхода"; exit 1
}
Ok "Файл: $(Split-Path $File -Leaf) ($([math]::Round((Get-Item $File).Length/1KB,1)) КБ)"

# ---------------------------------------------------------------------------
# 2. Пароль
# ---------------------------------------------------------------------------
Step "2/4 Пароль"
if (-not $Password) {
    $secure = Read-Host "Введите пароль" -AsSecureString
    $Password = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure))
}
if (-not $Password) {
    Fail "Пароль не введён"; Read-Host "Нажмите Enter для выхода"; exit 1
}

# ---------------------------------------------------------------------------
# 3. Расшифровка
# ---------------------------------------------------------------------------
Step "3/4 Расшифровка"
if (-not $OutputPath) {
    $base = [IO.Path]::GetFileNameWithoutExtension($File)
    $base = $base -replace '_encrypted$', ''
    $OutputPath = Join-Path (Split-Path $File -Parent) "$base.zip"
}

$inStream = [System.IO.File]::OpenRead($File)
try {
    # Проверяем магию
    $magic = New-Object byte[] 4
    $inStream.Read($magic, 0, 4) | Out-Null
    if ([System.Text.Encoding]::ASCII.GetString($magic) -ne 'AHE1') {
        Fail "Неверный формат файла (ожидается AHE1). Возможно, файл повреждён."
        $inStream.Dispose(); Read-Host "Нажмите Enter для выхода"; exit 1
    }

    # Читаем соль и IV
    $salt = New-Object byte[] 16
    $iv = New-Object byte[] 16
    $inStream.Read($salt, 0, 16) | Out-Null
    $inStream.Read($iv, 0, 16) | Out-Null

    # Ключ из пароля
    $iterations = 200000
    $kdf = New-Object System.Security.Cryptography.Rfc2898DeriveBytes(
        $Password, $salt, $iterations, [System.Security.Cryptography.HashAlgorithmName]::SHA256)
    $key = $kdf.GetBytes(32)

    $aes = [System.Security.Cryptography.Aes]::Create()
    $aes.KeySize = 256
    $aes.Key = $key
    $aes.IV = $iv
    $aes.Mode = [System.Security.Cryptography.CipherMode]::CBC
    $aes.Padding = [System.Security.Cryptography.PaddingMode]::PKCS7
    $decryptor = $aes.CreateDecryptor()

    $outStream = [System.IO.File]::Create($OutputPath)
    try {
        $crypto = New-Object System.Security.Cryptography.CryptoStream(
            $inStream, $decryptor, [System.Security.Cryptography.CryptoStreamMode]::Read)
        $buffer = New-Object byte[] 81920
        while (($read = $crypto.Read($buffer, 0, $buffer.Length)) -gt 0) {
            $outStream.Write($buffer, 0, $read)
        }
        $crypto.Dispose()
    } finally {
        $outStream.Dispose()
        $aes.Dispose()
        $kdf.Dispose()
    }
} catch [System.Security.Cryptography.CryptographicException] {
    $inStream.Dispose()
    if (Test-Path -LiteralPath $OutputPath) { Remove-Item -LiteralPath $OutputPath -Force }
    Fail "ОШИБКА: неверный пароль или файл повреждён"
    Read-Host "Нажмите Enter для выхода"; exit 1
} finally {
    $inStream.Dispose()
}

Ok "Расшифровано: $(Split-Path $OutputPath -Leaf) ($([math]::Round((Get-Item $OutputPath).Length/1KB,1)) КБ)"

# ---------------------------------------------------------------------------
# 4. Распаковка
# ---------------------------------------------------------------------------
Step "4/4 Распаковка архива"
$extractDir = Join-Path $ProjectRoot "received"
if ($Extract) {
    if (Test-Path -LiteralPath $extractDir) { Remove-Item -LiteralPath $extractDir -Recurse -Force }
    New-Item -ItemType Directory -Force -Path $extractDir | Out-Null
    Expand-Archive -LiteralPath $OutputPath -DestinationPath $extractDir -Force
    $items = (Get-ChildItem -LiteralPath $extractDir).Count
    Ok "Распаковано в папку: received\ ($items объектов)"
} else {
    Write-Host "   Для распаковки выполните с параметром -Extract" -ForegroundColor Gray
    Write-Host "   или вручную распакуйте: $OutputPath" -ForegroundColor Gray
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "   РАСШИФРОВКА ЗАВЕРШЕНА" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "   Архив:   $OutputPath" -ForegroundColor White
if ($Extract) {
    Write-Host "   Папка:   $extractDir" -ForegroundColor White
}
Write-Host ""
Write-Host "   ДАЛЬНЕЙШИЕ ШАГИ:" -ForegroundColor Cyan
Write-Host "   1. Восстановить базу из дампа:" -ForegroundColor Gray
Write-Host "      powershell -File scripts\import_project.ps1 -DumpFile <путь>\database_dump.sql" -ForegroundColor White
Write-Host "   2. Или просто запустить: start.bat" -ForegroundColor Gray
Write-Host ""
