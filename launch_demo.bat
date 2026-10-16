@echo off
cd /d "%~dp0"
python --version >nul 2>&1
if errorlevel 1 (
  echo Install Python 3.11 or later and add it to PATH.
  pause
  exit /b 1
)
if not exist "demo_workspace\data\ledger.sqlite3" (
  python demo.py --days 14
  if errorlevel 1 (
    pause
    exit /b 1
  )
)
echo Opening the fictional SmartBus demonstration workspace.
python control_panel.py --root demo_workspace
pause
