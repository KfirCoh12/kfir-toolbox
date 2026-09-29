@echo off
setlocal
cd /d "%~dp0"
title Install Kfir Toolbox Local

where python >nul 2>&1
if errorlevel 1 (
  echo Python 3.12 or newer was not found on this PC.
  echo Install Python and enable "Add Python to PATH", then run this again.
  pause
  exit /b 1
)

python -m pip install -r requirements-local.txt
if errorlevel 1 (
  echo.
  echo Installation failed. Check the Python and pip messages above.
  pause
  exit /b 1
)

echo.
echo Kfir Toolbox local dependencies are installed.
pause
