@chcp 936 >nul
@echo off
title 赛博养Gemini - 开启开机静默常驻
cd /d "%~dp0"
echo ==========================================================
echo   正在配置赛博双子星 Windows 开机静默常驻自启...
echo ==========================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup_autostart.ps1"
if %errorlevel% equ 0 (
    echo.
    echo ==========================================================
    echo [成功] 开机静默常驻已成功部署！
    echo 电脑每次开机，双子星均会自动在后台静默唤醒守护。
    echo ==========================================================
) else (
    echo.
    echo [提示] 部署过程中存在告警，请确认权限。
)
ping 127.0.0.1 -n 4 >nul
