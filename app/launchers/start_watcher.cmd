@echo off
setlocal EnableExtensions
set "PROG=%~dp0..\"
if not exist "%PROG%radai_watcher.py" set "PROG=%~dp0"
set "JANELA=%~dp0open_browser.cmd"
set "LOGF=%PROG%radai_lancador.log"
cd /d "%PROG%"
set "TOTALSEG_WEIGHTS_PATH=%PROG%ts_weights"
set "PYTHONIOENCODING=utf-8:replace"

if not exist "%PROG%python\python.exe" (
  echo ERROR: could not find "%PROG%python\python.exe".
  echo It must run with the Python from the bundle ^(python\ folder^).
  >>"%LOGF%" echo %DATE% %TIME% start_watcher: python\python.exe not found
  echo.
  pause
  exit /b 1
)

set "URL=http://127.0.0.1:8777/"
set "PORTA="
set "CFGV=%PROG%radai_watcher.config"
if defined RADAI_CONFIG set "CFGV=%RADAI_CONFIG%"
if exist "%CFGV%" (
  for /f "usebackq tokens=1,* delims==" %%A in (`findstr /r /i /c:"^[^#ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_]*PORT *=" "%CFGV%"`) do (
    set "PORTA="
    for /f "tokens=1 delims=# " %%P in ("%%B") do set "PORTA=%%P"
  )
)
if defined PORTA for /f "delims=0123456789" %%X in ("%PORTA%") do set "PORTA="
if defined PORTA set "URL=http://127.0.0.1:%PORTA%/"

echo ============================================================
echo  Radioterapia.AI Local Suite
echo  Start:  %URL%       (all modules)
echo  Queue:  %URL%lote   (queue, log and controls)
echo  Log:    the Log tab in the panel, and Settings ^> Diagnostics
echo ============================================================
echo.
echo  Structures come out as UNAPPROVED SUGGESTIONS (_ai suffix).
echo  Review and approval remain a medical act, in the TPS.
echo.
REM GUARDA: com o radai_lancador o motor sobe sem janela e o proprio
REM lancador abre o navegador; sem ele (instalacao parcial) roda como antes.
if not exist "%PROG%radai_lancador.py" goto :visivel
"%PROG%python\python.exe" "%PROG%radai_lancador.py" --url %URL% --log "%LOGF%"
set "RC=%ERRORLEVEL%"
REM GUARDA: 90 e painel no ar sem navegador aberto pelo lancador (falta a
REM pagina de carregamento); o lote abre o navegador como antes.
if "%RC%"=="90" goto :navegador
if not "%RC%"=="0" goto :parou
endlocal & exit /b 0

:navegador
call "%JANELA%" %URL%
endlocal & exit /b 0

:visivel
echo  Study Queue - leave this window OPEN.
echo.
REM GUARDA: cmd /c call, e nao o .cmd direto: o start de um .cmd abre um
REM cmd /K que fica parado no prompt depois de o lote acabar.
start "" /min cmd /c call "%JANELA%" %URL%
"%PROG%python\python.exe" "%PROG%radai_watcher.py"
set "RC=%ERRORLEVEL%"

:parou

>>"%LOGF%" echo %DATE% %TIME% start_watcher: stopped with code %RC%
echo.
if not "%RC%"=="0" (
  echo ============================================================
  echo  THE STUDY QUEUE STOPPED with code %RC%.
  echo  See the log in the panel's Log tab ^(%URL%lote^).
  echo  Send that log to whoever administers this installation.
  echo ============================================================
) else (
  echo Vigia encerrado.
)
echo.
pause
endlocal & exit /b %RC%
