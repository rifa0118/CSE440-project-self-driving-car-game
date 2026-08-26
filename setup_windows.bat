@echo off
setlocal EnableExtensions
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
  set "PYTHON=py -3"
) else (
  where python >nul 2>nul
  if not %errorlevel%==0 (
    echo Python 3.10 or newer was not found.
    echo Install 64-bit Python from python.org and enable "Add Python to PATH", then run this file again.
    pause
    exit /b 1
  )
  set "PYTHON=python"
)

%PYTHON% -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" || (
  echo Python 3.10 or newer is required.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating isolated virtual environment...
  %PYTHON% -m venv .venv || goto :error
)

set "VENV_PY=.venv\Scripts\python.exe"

echo Upgrading pip...
%VENV_PY% -m pip install --upgrade pip || goto :error

echo Installing runtime and verification dependencies...
%VENV_PY% -m pip install -r requirements-dev.txt || goto :error

echo Generating and validating track assets...
%VENV_PY% main.py generate-assets || goto :error

echo Running release preflight...
%VENV_PY% -m compileall -q ai game utils main.py config.py || goto :error
%VENV_PY% tools\verify_release.py --strict-pygame --episodes 5 --output verification\setup_preflight.json || goto :error
%VENV_PY% -m pip check || goto :error

echo.
echo Setup complete and preflight passed.
echo Double-click run_game.bat to start the game.
echo Run verify_project.bat before the final presentation for the full 20-episode-per-track verification.
pause
exit /b 0

:error
echo.
echo Setup failed. Read docs\USER_GUIDE.md for troubleshooting.
pause
exit /b 1
