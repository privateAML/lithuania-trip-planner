@echo off
cd /d "%~dp0"
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo Setup failed. Check Python and your internet connection.
  pause
  exit /b 1
)
echo Setup complete. Open launch.pyw.
pause
