@echo off
REM ===========================================================================
REM  College Information System - one-click launcher
REM  Checks environment, prepares the database and starts the server.
REM ===========================================================================
chcp 65001 > nul
title College IS - starting
echo ============================================================
echo   College Information System - start
echo ============================================================
echo.

REM Проверка наличия PowerShell
where powershell > nul 2>&1
if errorlevel 1 (
    echo [ERROR] PowerShell not found in PATH
    pause
    exit /b 1
)

REM Запуск основного скрипта
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start.ps1" %*
set EXITCODE=%ERRORLEVEL%

if not "%EXITCODE%"=="0" (
    echo.
    echo [ERROR] start.ps1 exited with code %EXITCODE%
    echo Check the messages above.
    pause
)
