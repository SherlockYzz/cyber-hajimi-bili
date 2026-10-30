@chcp 936 >nul
@echo off
title 停止赛博哈基米守护进程
cd /d "%~dp0"
echo ==========================================================
echo   正在停止赛博哈基米后台所有进程...
echo ==========================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\remove_autostart.ps1"
powershell -NoProfile -Command "$conn = Get-NetTCPConnection -LocalPort 8765 -ErrorAction SilentlyContinue; if ($conn) { foreach ($p in $conn.OwningProcess | Select-Object -Unique) { Stop-Process -Id $p -Force -ErrorAction SilentlyContinue } }"
taskkill /F /IM pythonw.exe 2>nul
echo [完成] 后台常驻已全部安全终止。
ping 127.0.0.1 -n 2 >nul
