# -*- coding: utf-8 -*-
<#
.SYNOPSIS
    一键关闭赛博养Gemini的 Windows 开机常驻自启
.DESCRIPTION
    清理 Windows 启动文件夹中的快捷方式。
#>

[CmdletBinding()]
param()

$StartupFolder = [Environment]::GetFolderPath("Startup")
$ShortcutPath = Join-Path $StartupFolder "赛博养Gemini_双子星.lnk"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " 🐾 赛博养Gemini - 关闭开机常驻自启 " -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan

if (Test-Path $ShortcutPath) {
    Remove-Item -Path $ShortcutPath -Force
    Write-Host "[✅ 成功] 已成功移除开机自启快捷方式！" -ForegroundColor Green
    Write-Host "  👉 已清理: $ShortcutPath" -ForegroundColor Gray
} else {
    Write-Host "[ℹ️ 提示] 当前未设置开机自启快捷方式。" -ForegroundColor Yellow
}
