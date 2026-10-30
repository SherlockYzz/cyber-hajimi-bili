@chcp 936 >nul
@echo off
title 停止赛博哈基米守护进程
cd /d "%~dp0"
echo ==========================================================
echo   正在停止赛博哈基米后台所有进程...
echo ==========================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\remove_autostart.ps1"
taskkill /F /IM pythonw.exe /FI "WINDOWTITLE eq *" 2>nul
taskkill /F /IM python.exe /FI "WINDOWTITLE eq 赛博养Gemini*" 2>nul
echo [完成] 后台常驻已全部安全终止。
ping 127.0.0.1 -n 2 >nul
