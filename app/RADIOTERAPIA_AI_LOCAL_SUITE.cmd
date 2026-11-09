@echo off
cd /d "%~dp0"

set "ALVO="
if exist "%~dp0launchers\start_watcher.cmd"    set "ALVO=%~dp0launchers\"
if not defined ALVO if exist "%~dp0ferramentas\start_watcher.cmd" set "ALVO=%~dp0ferramentas\"
if not defined ALVO if exist "%~dp0start_watcher.cmd" set "ALVO=%~dp0"
if not defined ALVO (
  echo.
  echo   ============================================================
  echo    INCOMPLETE INSTALLATION
  echo   ============================================================
  echo.
  echo    Could not find start_watcher.cmd. Looked in:
  echo      "%~dp0launchers\"
  echo      "%~dp0ferramentas\"
  echo      "%~dp0"
  echo.
  echo    This is usually a half-finished copy. Copy the WHOLE
  echo    program folder from inside the package.
  echo   ============================================================
  echo.
  >>"%~dp0radai_lancador.log" echo %DATE% %TIME% RADIOTERAPIA_AI_LOCAL_SUITE: start_watcher.cmd not found
  pause
  exit /b 1
)

call "%ALVO%start_watcher.cmd"
exit /b %ERRORLEVEL%
