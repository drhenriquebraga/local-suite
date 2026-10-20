@echo off
setlocal
cd /d "%~dp0"

echo.
echo   Radioterapia.ai Local Suite - Preparer
echo   --------------------------------------
echo.
echo   Opening the preparer window...
echo.

set "LOGDIR=%LOCALAPPDATA%\RadioterapiaAI\logs"
if "%LOCALAPPDATA%"=="" set "LOGDIR=%USERPROFILE%\RadioterapiaAI\logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%" 2>nul
if not exist "%LOGDIR%" set "LOGDIR=%TEMP%"
set "STAMP="
for /f "usebackq delims=" %%T in (`powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"`) do set "STAMP=%%T"
if not defined STAMP set "STAMP=%RANDOM%%RANDOM%"
set "RADAI_LOG_PREPARADOR=%LOGDIR%\preparer_%STAMP%.log"
>> "%RADAI_LOG_PREPARADOR%" echo PREPARAR_AUTO_CONTORNO.cmd started %DATE% %TIME%
set "RADAI_AJUDA_LOG=%~dp0preparer_log.ps1"
if exist "%RADAI_AJUDA_LOG%" powershell -NoProfile -ExecutionPolicy Bypass -File "%RADAI_AJUDA_LOG%" -Modo Podar >nul 2>&1
echo   The preparer log is kept at
echo     %RADAI_LOG_PREPARADOR%
echo.

powershell -NoProfile -ExecutionPolicy Bypass -STA -File "%~dp0prepare.ps1" >> "%RADAI_LOG_PREPARADOR%" 2>&1
set "RC=%ERRORLEVEL%"
>> "%RADAI_LOG_PREPARADOR%" echo PREPARAR_AUTO_CONTORNO.cmd: the preparer exited with code %RC% at %DATE% %TIME%

set "RADAI_RC=%RC%"
if not "%RC%"=="0" (
  echo.
  echo   ============================================================
  echo   The preparer stopped with error %RC%.
  echo.
  echo   Its log is kept at
  echo     "%RADAI_LOG_PREPARADOR%"
  echo   Please send this file together with your report.
  echo.
  echo   The last 15 lines of that log:
  echo   ------------------------------------------------------------
  if exist "%RADAI_AJUDA_LOG%" powershell -NoProfile -ExecutionPolicy Bypass -File "%RADAI_AJUDA_LOG%" -Modo Cauda
  if not exist "%RADAI_AJUDA_LOG%" echo   [the log reader is missing - open the file above]
  echo   ------------------------------------------------------------
  echo.
  echo   If the message mentioned execution policy or a blocked
  echo   script, read README.txt in this folder: there is a path
  echo   that does not need scripts to be unblocked.
  echo   ============================================================
  echo.
)

echo.
pause
endlocal & exit /b %RC%
