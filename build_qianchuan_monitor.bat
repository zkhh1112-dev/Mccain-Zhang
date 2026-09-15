@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_qianchuan_monitor.ps1"
if errorlevel 1 pause
endlocal
