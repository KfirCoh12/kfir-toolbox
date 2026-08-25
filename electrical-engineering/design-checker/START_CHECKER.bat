@echo off
setlocal
cd /d "%~dp0"
title Electrical Design Checker

where python >nul 2>&1
if errorlevel 1 (
  echo Python was not found on this PC.
  echo Install Python and make sure it is added to PATH, then try again.
  pause
  exit /b 1
)

python -m streamlit run app.py

if errorlevel 1 (
  echo.
  echo The checker could not start.
  echo If Streamlit is missing, run: python -m pip install -r requirements.txt
  pause
)
