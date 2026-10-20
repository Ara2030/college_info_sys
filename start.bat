@echo off
chcp 65001 > nul
title Информационная система колледжа - запуск
REM ===========================================================================
REM  ИС колледжа (СПО) - запуск одним кликом.
REM  Проверяет окружение, готовит базу данных и запускает сервер.
REM  Параметры: -Port 8080  -NoBrowser  -SkipDemo
REM ===========================================================================
echo ============================================================
echo   Информационная система колледжа - запуск
echo ============================================================
echo.

where powershell > nul 2>&1
if errorlevel 1 goto nops

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start.ps1" %*
set "EXITCODE=%ERRORLEVEL%"

if not "%EXITCODE%"=="0" goto failed
goto end

:nops
echo [ОШИБКА] PowerShell не найден в PATH.
pause
exit /b 1

:failed
echo.
echo [ОШИБКА] Запуск прерван, код %EXITCODE%. Смотрите сообщения выше.
pause

:end