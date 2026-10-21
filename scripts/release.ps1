# ============================================================================
#  СБОРКА РЕЛИЗА ДЛЯ АВТООБНОВЛЕНИЯ
#  Готовит архив с кодом, version.json (манифест) и, при наличии gh, публикует
#  релиз на GitHub. Клиентские машины забирают обновление из манифеста.
#
#  Примеры:
#    powershell -File scripts\release.ps1 -Version 1.0.1 -Notes "Исправлены даты"
#    powershell -File scripts\release.ps1 -Version 1.0.1 -Publish
# ============================================================================
param(
    [Parameter(Mandatory = $true)][string]$Version,
    [string]$Notes = "",
    [string]$BaseUrl = "",      # куда будет выложен архив (по умолчанию GitHub Releases)
    [switch]$Publish,           # опубликовать релиз через gh
    [string]$Repo = "Ara2030/college_info_sys"
)

$ErrorActionPreference = "Stop"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }

$root = Split-Path $PSScriptRoot -Parent
$outDir = Join-Path $root "dist\releases"
$workDir = Join-Path $env:TEMP ("college_release_" + $Version)

if ($Version -notmatch '^\d+\.\d+\.\d+$') {
    throw "Версия должна быть в формате X.Y.Z, например 1.0.1"
}

Write-Host "== Сборка релиза $Version" -ForegroundColor Cyan

# 1. Версия в проекте
[System.IO.File]::WriteAllText((Join-Path $root "VERSION"), "$Version`r`n",
    (New-Object System.Text.UTF8Encoding($false)))
Write-Host "   VERSION = $Version" -ForegroundColor Green

# 2. Копия кода без служебных папок
Remove-Item -LiteralPath $workDir -Recurse -Force -ErrorAction SilentlyContinue
$srcDir = Join-Path $workDir "app"
& robocopy $root $srcDir /E /NFL /NDL /NJH /NJS /R:1 /W:1 /XD `
    "$root\.venv" "$root\.git" "$root\logs" "$root\media" "$root\backups" `
    "$root\_install" "$root\dist" "$root\installer" "$root\__pycache__" `
    /XF "$root\.env" | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy завершился с кодом $LASTEXITCODE" }

# Чистим кэш Python из архива
Get-ChildItem $srcDir -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# 3. Архив
New-Item -ItemType Directory -Path $outDir -Force | Out-Null
$zipName = "CollegeIS-$Version.zip"
$zipPath = Join-Path $outDir $zipName
Remove-Item -LiteralPath $zipPath -Force -ErrorAction SilentlyContinue
Compress-Archive -Path (Join-Path $srcDir "*") -DestinationPath $zipPath -Force
$sizeMb = [math]::Round((Get-Item $zipPath).Length / 1MB, 1)
Write-Host "   архив: dist\releases\$zipName ($sizeMb МБ)" -ForegroundColor Green

# 4. Манифест
$sha = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash
if (-not $BaseUrl) {
    $BaseUrl = "https://github.com/$Repo/releases/download/v$Version"
}
$manifest = [ordered]@{
    version = $Version
    date    = (Get-Date -Format 'yyyy-MM-dd')
    url     = "$($BaseUrl.TrimEnd('/'))/$zipName"
    sha256  = $sha
    notes   = $Notes
}
$manifestPath = Join-Path $outDir "version.json"
[System.IO.File]::WriteAllText($manifestPath, ($manifest | ConvertTo-Json),
    (New-Object System.Text.UTF8Encoding($false)))
Write-Host "   манифест: dist\releases\version.json" -ForegroundColor Green
Write-Host "   SHA256: $sha" -ForegroundColor Gray

# 5. Публикация
if ($Publish) {
    $gh = Get-Command gh -ErrorAction SilentlyContinue
    if (-not $gh) {
        Write-Host "   gh не установлен - опубликуйте вручную:" -ForegroundColor Yellow
        Write-Host "     gh release create v$Version `"$zipPath`" `"$manifestPath`" --title `"$Version`" --notes `"$Notes`"" -ForegroundColor Yellow
    } else {
        & gh release create "v$Version" $zipPath $manifestPath --repo $Repo --title $Version --notes $Notes
        if ($LASTEXITCODE -ne 0) { throw "gh release create завершился с ошибкой" }
        Write-Host "   релиз v$Version опубликован" -ForegroundColor Green
    }
} else {
    Write-Host "   публикация пропущена (запустите с -Publish или загрузите архив и version.json вручную)" -ForegroundColor Gray
}

Remove-Item -LiteralPath $workDir -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "== Готово" -ForegroundColor Cyan
