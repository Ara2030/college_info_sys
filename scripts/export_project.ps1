# ============================================================================
#  ЭКСПОРТ ИС КОЛЛЕДЖА для передачи другому человеку
#  Создаёт папку dist/ с архивом проекта, дампом БД и инструкцией.
#  Запуск: powershell -ExecutionPolicy Bypass -File scripts\export_project.ps1
# ============================================================================
param(
    [string]$DbName = "college_sys",
    [string]$DbUser = "postgres",
    [string]$DbHost = "127.0.0.1",
    [string]$OutDir = ""
)

$ErrorActionPreference = "Continue"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }
$ProjectRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $ProjectRoot

function Step($t) { Write-Host "`n>> $t" -ForegroundColor Cyan }
function Ok($t)   { Write-Host "   OK  $t" -ForegroundColor Green }
function Warn($t) { Write-Host "   !   $t" -ForegroundColor Yellow }

if (-not $OutDir) { $OutDir = Join-Path $ProjectRoot "dist" }
if (-not (Test-Path -LiteralPath $OutDir)) { New-Item -ItemType Directory -Force -Path $OutDir | Out-Null }

$stamp = Get-Date -Format "yyyy-MM-dd"
Write-Host "============================================================" -ForegroundColor White
Write-Host "   ЭКСПОРТ ИС КОЛЛЕДЖА ДЛЯ ПЕРЕДАЧИ" -ForegroundColor White
Write-Host "============================================================" -ForegroundColor White

# ---------------------------------------------------------------------------
# 1. Дамп базы данных
# ---------------------------------------------------------------------------
Step "1/4 Создание дампа базы данных"
$dumpFile = Join-Path $OutDir "database_dump.sql"
$pgDump = "C:\Program Files\PostgreSQL\17\bin\pg_dump.exe"
if (-not (Test-Path -LiteralPath $pgDump)) { $pgDump = "pg_dump" }

$env:PGPASSWORD = ""
& $pgDump -U $DbUser -h $DbHost -d $DbName --no-owner --no-privileges -f $dumpFile 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    $size = [math]::Round((Get-Item -LiteralPath $dumpFile).Length / 1KB, 1)
    Ok "Дамп БД: database_dump.sql ($size КБ)"
} else {
    Warn "Не удалось создать дамп БД (проверьте PostgreSQL и имя базы)"
}

# ---------------------------------------------------------------------------
# 2. Копия проекта без временных и секретных файлов
# ---------------------------------------------------------------------------
Step "2/4 Подготовка копии проекта"
$stageDir = Join-Path $OutDir "college_info_sys"
if (Test-Path -LiteralPath $stageDir) { Remove-Item -LiteralPath $stageDir -Recurse -Force }
New-Item -ItemType Directory -Force -Path $stageDir | Out-Null

# Что НЕ копируем: окружение, кэш Python, секреты, временные данные
$excludeDirs = @('.venv', '__pycache__', '.git', '.idea', '.vscode', 'dist',
                 'logs', 'backups', 'media', 'node_modules', '.pytest_cache',
                 '.gigacode', '.mypy_cache')
$excludeFiles = @('.env', 'db.sqlite3', '*.pyc')

# robocopy копирует рекурсивно и исключает каталоги на ВСЕХ уровнях
$roboArgs = @($ProjectRoot, $stageDir, '/E', '/NFL', '/NDL', '/NJH', '/NJS', '/NP', '/R:1', '/W:1')
$roboArgs += '/XD'
$roboArgs += $excludeDirs
$roboArgs += '/XF'
$roboArgs += $excludeFiles
& robocopy @roboArgs | Out-Null
if ($LASTEXITCODE -lt 8) {
    Ok "Файлы проекта скопированы (без .venv, .env, __pycache__, logs, media)"
} else {
    Warn "Копирование файлов завершилось с кодом $LASTEXITCODE"
}

# Удаляем возможные остатки кэша Python
Get-ChildItem -LiteralPath $stageDir -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
    ForEach-Object { Remove-Item -LiteralPath $_.FullName -Recurse -Force -ErrorAction SilentlyContinue }
Get-ChildItem -LiteralPath $stageDir -Recurse -File -Filter "*.pyc" -ErrorAction SilentlyContinue |
    ForEach-Object { Remove-Item -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue }

# Секреты не передаём - только шаблон
if (Test-Path -LiteralPath (Join-Path $stageDir ".env.example")) {
    Ok "Шаблон .env.example включён (секреты не передаются)"
}

# ---------------------------------------------------------------------------
# 3. Инструкция для получателя
# ---------------------------------------------------------------------------
Step "3/4 Создание инструкции для получателя"
$readme = @'
ИНСТРУКЦИЯ ПО РАЗВЁРТЫВАНИЮ ИС КОЛЛЕДЖА
=======================================

Что в архиве:
  college_info_sys/     - исходный код системы (Django-проект)
  database_dump.sql     - дамп базы данных (все данные: студенты, оценки, расписание и т.д.)
  README_УСТАНОВКА.txt  - этот файл

ТРЕБОВАНИЯ
----------
1. Python 3.12 или новее        (проверить: python --version)
2. PostgreSQL 15 или новее      (скачать: https://www.postgresql.org/download/windows/)
3. Git (необязательно)

УСТАНОВКА - ПОШАГОВО
--------------------
Шаг 1. Установите Python и PostgreSQL (при установке PostgreSQL запомните пароль
       пользователя postgres! Он понадобится).

Шаг 2. Распакуйте архив, например в C:\college_info_sys

Шаг 3. Создайте базу данных. Откройте командную строку (cmd) и выполните:

       "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -c "CREATE DATABASE college_sys ENCODING 'UTF8' TEMPLATE template0;"

       (введите пароль postgres, когда попросит)

Шаг 4. Восстановите данные из дампа:

       "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -d college_sys -f database_dump.sql

Шаг 5. Создайте файл .env в папке проекта (скопируйте .env.example и переименуйте).
       Откройте его в блокноте и укажите:

       DJANGO_DEBUG=True
       DJANGO_SECRET_KEY=<любая длинная случайная строка>
       DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
       DB_NAME=college_sys
       DB_USER=postgres
       DB_PASSWORD=<ваш пароль postgres>
       DB_HOST=127.0.0.1
       DB_PORT=5432

Шаг 6. Запустите систему - двойной щелчок по start.bat
       (скрипт сам создаст окружение, поставит зависимости и запустит сервер)

Шаг 7. Откройте браузер:  http://127.0.0.1:8000/

ВХОД В СИСТЕМУ
--------------
  admin / admin123          - администратор
  director / director123    - директор
  methodist / methodist123  - методист
  teacher1 / teacher123     - преподаватель
  student1 / student123     - студент
  parent1 / parent123       - родитель

ВАЖНО: смените пароли в реальной эксплуатации!

ЕСЛИ ЧТО-ТО НЕ РАБОТАЕТ
-----------------------
- Ошибка подключения к БД → проверьте, что служба PostgreSQL запущена
  (Пуск → Службы → postgresql-x64-17 → Запустить) и пароль в .env верный.
- Нет прав на миграции → запустите от имени администратора.
- Подробная документация: файл README.md в папке проекта.
- Раздел "Возможные проблемы" в README.md содержит решения типовых ошибок.

АЛЬТЕРНАТИВА: если PostgreSQL установить нельзя
----------------------------------------------
Можно использовать SQLite (без установки СУБД). В файле config/settings.py
замените блок DATABASES на:

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

Затем выполните: python manage.py migrate (данные будут пустыми - заполнить
демо-данными можно скриптом: python fill_demo_data.py).
'@
$readmePath = Join-Path $stageDir "README_УСТАНОВКА.txt"
$readme | Set-Content -LiteralPath $readmePath -Encoding UTF8
Ok "Инструкция README_УСТАНОВКА.txt создана"

# ---------------------------------------------------------------------------
# 4. Архив
# ---------------------------------------------------------------------------
Step "4/4 Упаковка в архив"
$zipFile = Join-Path $OutDir "college_info_sys_$stamp.zip"
if (Test-Path -LiteralPath $zipFile) { Remove-Item -LiteralPath $zipFile -Force }
Compress-Archive -Path (Join-Path $stageDir "*") -DestinationPath $zipFile -CompressionLevel Optimal
$zipSize = [math]::Round((Get-Item -LiteralPath $zipFile).Length / 1MB, 2)
Ok "Архив: $(Split-Path $zipFile -Leaf) ($zipSize МБ)"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "   ЭКСПОРТ ЗАВЕРШЁН" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "   Папка для передачи: $OutDir" -ForegroundColor White
Write-Host ""
Write-Host "   Что передать получателю:" -ForegroundColor White
Write-Host "   1. $zipFile"
Write-Host "   2. database_dump.sql" -ForegroundColor White
Write-Host ""
Write-Host "   Способ передачи: облако (Яндекс.Диск, Google Drive)," -ForegroundColor Gray
Write-Host "   флешка, e-mail (если размер позволяет) или Git." -ForegroundColor Gray
Write-Host ""
