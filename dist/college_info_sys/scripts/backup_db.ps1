# ============================================================
# Резервное копирование базы данных ИС колледжа (PostgreSQL)
# Запуск: powershell -ExecutionPolicy Bypass -File scripts\backup_db.ps1
# ============================================================
param(
    [string]$DbName = "college_sys",
    [string]$DbUser = "postgres",
    [string]$DbHost = "127.0.0.1",
    [string]$BackupDir = ""
)

$ErrorActionPreference = "Stop"

# Папка для бэкапов (по умолчанию - backups в корне проекта)
if (-not $BackupDir) {
    $BackupDir = Join-Path (Split-Path $PSScriptRoot -Parent) "backups"
}
if (-not (Test-Path -LiteralPath $BackupDir)) {
    New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
}

# Поиск pg_dump
$pgDump = Join-Path "C:\Program Files\PostgreSQL\17\bin" "pg_dump.exe"
if (-not (Test-Path -LiteralPath $pgDump)) {
    $pgDump = "pg_dump"   # из PATH
}

$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm"
$file = Join-Path $BackupDir "college_sys_$timestamp.sql"

Write-Output "Создание резервной копии БД $DbName ..."
& $pgDump -U $DbUser -h $DbHost -d $DbName --no-owner --no-privileges -f $file

if ($LASTEXITCODE -eq 0) {
    $size = [math]::Round((Get-Item -LiteralPath $file).Length / 1KB, 1)
    Write-Output "OK: $file ($size КБ)"

    # Ротация: оставляем последние 10 копий
    Get-ChildItem -LiteralPath $BackupDir -Filter "college_sys_*.sql" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -Skip 10 |
        ForEach-Object {
            Remove-Item -LiteralPath $_.FullName -Force
            Write-Output "Удалена старая копия: $($_.Name)"
        }
} else {
    Write-Error "Ошибка резервного копирования (код $LASTEXITCODE)"
}
