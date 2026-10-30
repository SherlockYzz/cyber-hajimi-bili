@chcp 936 >nul
@echo off
title 赛博养Gemini - 控制中心启动器
cd /d "%~dp0"

echo ========================================================
echo   赛博养Gemini · 闪闪 (Gemini 3.8 Flash) 控制中心
echo ========================================================
echo 正在检查本地伴生服务状态...

netstat -ano | findstr ":8765" | findstr "LISTENING" >nul
if %errorlevel% equ 0 (
    echo [提示] 伴生服务已在后台运行中，正在调起浏览器...
    start http://127.0.0.1:8765/
) else (
    echo [启动] 正在唤醒伴生服务...
    start "Cyber-Hajimi-Web" python "src\hajimi_web_ui.py" --no-browser
    timeout /t 2 /nobreak >nul
    start http://127.0.0.1:8765/
    echo [成功] 控制中心已打开！
)
echo.
echo 访问入口: http://127.0.0.1:8765/
echo 提示: 页面已打开，若无需查看日志可按任意键退出本窗口。
timeout /t 5 >nul