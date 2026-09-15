@echo off
REM ============================================================================
REM  College Information System - one-click launcher
REM  Checks environment, prepares the database and starts the server.
REM ============================================================================
chcp 65001 > nul
title College IS - starting
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start.ps1"
if errorlevel 1 (
    echo.
    echo An error occurred. Please check the messages above.
    pause
)
