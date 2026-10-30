@chcp 936 >nul
@echo off
title 赛博哈基米 - 一键安装到 Antigravity
cd /d "%~dp0"
echo ==========================================================
echo   正在将赛博哈基米一键安装至 Antigravity 全局插件中心...
echo ==========================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install_plugin.ps1"
pause
