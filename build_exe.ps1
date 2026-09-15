$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"

Set-Location $projectRoot

if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Host "正在创建 Python 虚拟环境..." -ForegroundColor Cyan
    py -3 -m venv ".venv"
}

Write-Host "正在准备打包工具..." -ForegroundColor Cyan
& $venvPython -m pip install -r "requirements-desktop.txt"

Write-Host "正在生成 Windows 软件..." -ForegroundColor Cyan
& $venvPython -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name "LiveStreamAgent" `
    "desktop_app.py"

if ($LASTEXITCODE -ne 0) {
    throw "软件打包失败，退出码：$LASTEXITCODE"
}

$outputPath = Join-Path $projectRoot "dist\LiveStreamAgent.exe"
Write-Host ""
Write-Host "打包完成：$outputPath" -ForegroundColor Green
