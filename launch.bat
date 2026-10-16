@echo off
setlocal
cd /d "%~dp0"
title SmartBus Professional - Local Finance Workstation
py -3 -c "import sys; assert sys.version_info >= (3, 11)" >nul 2>nul
if not errorlevel 1 (
  py -3 control_panel.py %*
  goto finished
)
python -c "import sys; assert sys.version_info >= (3, 11)" >nul 2>nul
if not errorlevel 1 (
  python control_panel.py %*
  goto finished
)
if exist "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" (
  "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" control_panel.py %*
  goto finished
)
echo SmartBus needs Python 3.11 or newer. Install Python and enable the Python launcher.
echo Then double-click launch.bat again. No additional Python packages are required.
pause
exit /b 1
:finished
if errorlevel 1 (
  echo SmartBus could not start or encountered an error. See the message above.
  pause
)
endlocal
