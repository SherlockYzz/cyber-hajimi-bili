@chcp 936 >nul
@echo off
title 赛博养Gemini - 闪闪调度器
cd /d "%~dp0\.."
if "%1"=="" (
    python "src\hajimi_daemon.py"
) else if "%1"=="web" (
    python "src\hajimi_web_ui.py"
) else if "%1"=="cruise" (
    python "src\hajimi_daemon.py" --cruise
) else if "%1"=="morning" (
    python "src\hajimi_daemon.py" --morning
) else if "%1"=="evening" (
    python "src\hajimi_daemon.py" --evening
) else if "%1"=="login" (
    python "src\bili_hajimi_core.py" login
) else (
    echo 用法: %~nx0 [web|cruise|morning|evening|login]
)