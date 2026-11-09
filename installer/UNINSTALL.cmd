@echo off
setlocal
cd /d "%~dp0"

if not exist "%~dp0UNINSTALL.ps1" (
  echo.
  echo   Could not find UNINSTALL.ps1 next to this file.
  echo   This is usually a half-finished copy.
  echo.
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0UNINSTALL.ps1"
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
  echo.
  pause
)
endlocal & exit /b %RC%
