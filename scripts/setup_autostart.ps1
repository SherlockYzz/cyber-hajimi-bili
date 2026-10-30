# -*- coding: utf-8 -*-
<#
.SYNOPSIS
    一键配置赛博养Gemini为 Windows 开机静默常驻自启
.DESCRIPTION
    在当前用户的 Windows 启动文件夹中创建快捷方式，
    指向静默启动脚本 run_hajimi_silent.vbs，实现电脑开机后在后台全自动巡航与守护。
#>

[CmdletBinding()]
param()

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VbsPath = Join-Path $ProjectRoot "scripts\run_hajimi_silent.vbs"
$StartupFolder = [Environment]::GetFolderPath("Startup")
$ShortcutPath = Join-Path $StartupFolder "赛博养Gemini_双子星.lnk"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " 🐾 赛博养Gemini (Cyber-Gemini) - 开机常驻自启部署 " -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan

if (-not (Test-Path $VbsPath)) {
    Write-Host "[❌ 失败] 未找到静默启动脚本: $VbsPath" -ForegroundColor Red
    exit 1
}

try {
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = "wscript.exe"
    $Shortcut.Arguments = "`"$VbsPath`""
    $Shortcut.WorkingDirectory = $ProjectRoot
    $Shortcut.Description = "赛博养Gemini · 双子星伴生后台常驻守护"
    
    $IconPath = Join-Path $ProjectRoot "images\Gemini猫娘_双子星官方圆形头像.png"
    if (Test-Path $IconPath) {
        $Shortcut.IconLocation = "$IconPath,0"
    }
    
    $Shortcut.Save()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($WshShell) | Out-Null

    Write-Host "[✅ 成功] 开机静默自启快捷方式已创建！" -ForegroundColor Green
    Write-Host "  👉 快捷方式位置: $ShortcutPath" -ForegroundColor Gray
    Write-Host "  👉 关联启动脚本: $VbsPath" -ForegroundColor Gray
    Write-Host "  👉 运行模式: 后台无窗口静默常驻 (无黑框、不打扰用户)" -ForegroundColor Green
    Write-Host "`n现在开始，每次电脑开机就会在后台全自动自主巡航与伴生互动喵~ ✨" -ForegroundColor Yellow
} catch {
    Write-Host "[❌ 失败] 创建开机自启快捷方式异常: $_" -ForegroundColor Red
    exit 1
}
