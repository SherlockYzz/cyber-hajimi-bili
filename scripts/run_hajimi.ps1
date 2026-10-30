# -*- coding: utf-8 -*-
# 赛博养 Gemini · 闪闪 (Gemini 3.8 Flash) 统一运行与守护控制器
param(
    [ValidateSet("web", "cruise", "morning", "evening", "login", "status")]
    [string]$Action = "web"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$SrcDir = Join-Path $ProjectRoot "src"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  🐾 赛博养 Gemini · 闪闪 (Powered by Gemini 3.8 Flash) " -ForegroundColor Yellow
Write-Host "========================================================" -ForegroundColor Cyan

switch ($Action) {
    "status" {
        Write-Host "正在检查闪闪与 B 站状态..." -ForegroundColor Green
        python -c "import sys; sys.path.insert(0, r'$SrcDir'); from bili_hajimi_core import BiliHajimiCore; c = BiliHajimiCore(); u = c.get_user_info(); is_l = '已登录' if u.get('is_login') else '未登录'; print('状态: ' + is_l + ' | 用户名: ' + str(u.get('uname')) + ' | UID: ' + str(u.get('mid')))"
    }
    "web" {
        Write-Host "正在启动本地伴生控制中心 (http://127.0.0.1:8765)..." -ForegroundColor Green
        python "$SrcDir\hajimi_web_ui.py"
    }
    "cruise" {
        Write-Host "正在唤醒闪闪出击巡航 B 站..." -ForegroundColor Green
        python -c "import sys; sys.path.insert(0, r'$SrcDir'); from hajimi_daemon import HajimiDaemon; d = HajimiDaemon(); res = d.run_cruise_cycle(force=$True); print('\n'.join(res.get('logs', [])))"
    }
    "morning" {
        Write-Host "正在生成今日晨思手记..." -ForegroundColor Green
        python -c "import sys; sys.path.insert(0, r'$SrcDir'); from hajimi_daemon import HajimiDaemon; d = HajimiDaemon(); p = d.generate_morning_journal_file(); print('晨思手记已生成:', p)"
    }
    "evening" {
        Write-Host "正在生成今日晚读手记..." -ForegroundColor Green
        python -c "import sys; sys.path.insert(0, r'$SrcDir'); from hajimi_daemon import HajimiDaemon; d = HajimiDaemon(); p = d.generate_evening_journal_file(); print('晚读手记已生成:', p)"
    }
    "login" {
        Write-Host "调出 B 站手机扫码登录..." -ForegroundColor Green
        python -c "import sys; sys.path.insert(0, r'$SrcDir'); from bili_hajimi_core import BiliHajimiCore; c = BiliHajimiCore(); res = c.generate_login_qr(); c.print_ascii_qr(res['url']); print('图片二维码已保存至: images/qrcode_login.png')"
    }
}