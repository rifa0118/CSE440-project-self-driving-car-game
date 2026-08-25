@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo The virtual environment is missing. Run setup_windows.bat first.
  pause
  exit /b 1
)

set "PY=.venv\Scripts\python.exe"

echo [1/4] Compiling source...
%PY% -m compileall -q ai game utils main.py config.py || goto :error

echo [2/4] Running automated tests...
%PY% -m pytest -q || goto :error

echo [3/4] Running strict release verification, including Pygame dummy-display smoke test...
%PY% tools\verify_release.py --strict-pygame --episodes 20 --output verification\windows_verification.json || goto :error

echo [4/4] Checking installed package consistency...
%PY% -m pip check || goto :error

echo.
echo ALL PROJECT VERIFICATION CHECKS PASSED.
pause
exit /b 0

:error
echo.
echo PROJECT VERIFICATION FAILED. Review the output above.
pause
exit /b 1
