@echo off
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\pythonw.exe" (
  start "" ".venv\Scripts\pythonw.exe" "qianchuan_monitor_app.py"
) else (
  start "" pythonw "qianchuan_monitor_app.py"
)

endlocal
