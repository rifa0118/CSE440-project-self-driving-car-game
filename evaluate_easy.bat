@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run setup_windows.bat first.
  pause
  exit /b 1
)
.venv\Scripts\python.exe main.py evaluate --track easy --model models\easy_best.pth --episodes 20 --output results\evaluation_easy_manual.json
pause
