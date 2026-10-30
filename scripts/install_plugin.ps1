<#
.SYNOPSIS
    一键将赛博哈基米安装为 Antigravity 全局插件

.DESCRIPTION
    将当前工程目录无缝挂载至 Antigravity 用户插件目录 (~/.gemini/config/plugins/cyber-hajimi)
    并自动校验安装所需依赖。
#>

[CmdletBinding()]
param()

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PluginsDir = Join-Path $env:USERPROFILE ".gemini\config\plugins"
$TargetDir = Join-Path $PluginsDir "cyber-hajimi"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " 🐱 赛博哈基米 (Cyber-Hajimi) - Antigravity 插件安装器 " -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. 确保插件目录存在
if (-not (Test-Path $PluginsDir)) {
    New-Item -ItemType Directory -Path $PluginsDir -Force | Out-Null
}

# 2. 如果已存在旧的目标，安全清理
if (Test-Path $TargetDir) {
    Write-Host "[🔄更新检测] 发现已安装版本，正在刷新插件挂载..." -ForegroundColor DarkGray
    # 如果是目录联接或软链接直接删除，若是普通目录则递归清理
    cmd /c rmdir "$TargetDir" 2>$null
    if (Test-Path $TargetDir) {
        Remove-Item -Path $TargetDir -Recurse -Force
    }
}

# 3. 创建目录联接 (Junction)，免去管理员权限，且支持本地热更新！
Write-Host "[🔗建立关联] 正在将项目挂载至 Antigravity 插件生态..." -ForegroundColor Green
cmd /c mklink /J "$TargetDir" "$ProjectRoot"

if (Test-Path $TargetDir) {
    Write-Host "[✅挂载成功] 插件已安装至: $TargetDir" -ForegroundColor Green
} else {
    Write-Host "[⚠️降级方案] 目录联接失败，正在执行文件镜像拷贝..." -ForegroundColor Yellow
    Copy-Item -Path $ProjectRoot -Destination $TargetDir -Recurse -Force
}

# 4. 检查 Python 依赖
$ReqPath = Join-Path $ProjectRoot "requirements.txt"
if (Test-Path $ReqPath) {
    Write-Host "`n[📦依赖检查] 正在安装 Python 核心依赖..." -ForegroundColor Cyan
    python -m pip install -r $ReqPath --quiet
}

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host " 🎉 恭喜！赛博哈基米已成功安装到 Antigravity！" -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "即刻体验方式：" -ForegroundColor White
Write-Host "  1. 打开 Antigravity【插件管理 (Plugins)】页面，即可看到「赛博哈基米 (Cyber-Hajimi)」" -ForegroundColor Gray
Write-Host "  2. 在任何聊天窗口直接输入以下指令唤醒哈基米：" -ForegroundColor Gray
Write-Host "     - 唤醒哈基米，巡航今天的 B 站推荐流" -ForegroundColor DarkCyan
Write-Host "     - 让哈基米写一份今天的晚读精选生活手记" -ForegroundColor DarkCyan
Write-Host "     - 打开赛博哈基米控制中心" -ForegroundColor DarkCyan
Write-Host "==========================================================`n" -ForegroundColor Cyan
