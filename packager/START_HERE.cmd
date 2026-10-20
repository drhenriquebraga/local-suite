@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "CASA=%TEMP%\RadioterapiaAI_instalador"
set "AQUI=%~dp0"
if "%AQUI:~-1%"=="\" set "AQUI=%AQUI:~0,-1%"

echo.
echo   Radioterapia.ai Local Suite
echo   ===========================
echo.

call :achar_sub "%AQUI%"
set "SUB_AQUI=%SUB%"
call :achar_sub "%CASA%"
set "SUB_CASA=%SUB%"

if /i "%AQUI%"=="%CASA%" (
  echo   Running the installed copy at
  echo     "%CASA%"
  for %%F in ("%CASA%\%SUB_CASA%build\configurar_ambiente.py") do (
    if not "%%~tF"=="" echo   Esta copia e de %%~tF
  )
  echo.
  echo   Got a new package? Extract the .zip and click
  echo   START_HERE.cmd FROM INSIDE THE EXTRACTED FOLDER - that is
  echo   the one that updates this copy. Clicking this one runs what is here.
  echo.
  goto :rodar
)

if exist "%AQUI%\%SUB_AQUI%packager\prepare.ps1" (
  echo   Copying to "%CASA%"
  echo.
  if not exist "%CASA%" mkdir "%CASA%" 2>nul
  if not exist "%CASA%" (
    echo   WARNING: could not create
    echo     "%CASA%"
    echo   I will run from here instead.
    echo.
    set "CASA=%AQUI%"
    goto :rodar
  )
  xcopy "%AQUI%\*" "%CASA%\" /E /I /Y /Q >nul 2>&1
  REM  o xcopy leva o layout de AQUI inteiro; a casa fica igual
  set "SUB_CASA=%SUB_AQUI%"
  if not exist "%CASA%\%SUB_AQUI%packager\prepare.ps1" (
    echo   WARNING: the copy did not finish. Running from here instead.
    echo.
    set "CASA=%AQUI%"
  )
  goto :rodar
)

echo   You clicked from inside the .zip -- that is fine, it is what
echo   everyone does. Windows extracts only the file you clicked, so
echo   the rest of the package was left behind.
echo.
echo   I will look for the .zip and carry on. If I cannot find it,
echo   I will open a window for you to point at it.
echo.

set "RESP=%TEMP%\radai_zip_achado.txt"
if exist "%RESP%" del /q "%RESP%"
set "RADAI_SAIDA=%RESP%"
powershell -NoProfile -ExecutionPolicy Bypass -STA -Command "$ErrorActionPreference='SilentlyContinue';$n='RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_*.zip','RADIOTERAPIA_AI_LOCAL_SUITE_INSTALADOR_v*.zip','RADIOTERAPIA_AI_LOCAL_SUITE_BUNDLE_v*.zip','AUTO_CONTORNO_INSTALADOR_v*.zip','AUTO_CONTORNO*.zip'; $r=$null;try{$sh=New-Object -ComObject Shell.Application;foreach($w in $sh.Windows()){try{$p=$w.Document.Folder.Self.Path;if($p -and $p.ToLower().EndsWith('.zip') -and (Test-Path -LiteralPath $p)){$r=$p;break}}catch{}}}catch{};if(-not $r){$alvos=@();foreach($s in 'Downloads','Desktop','Documents'){$alvos+=(Join-Path $env:USERPROFILE $s)};$alvos+=$env:USERPROFILE;foreach($d in (Get-PSDrive -PSProvider FileSystem)){$alvos+=$d.Root};foreach($a in $alvos){foreach($nm in $n){$c=(Get-ChildItem -Path (Join-Path $a $nm) -File -EA SilentlyContinue |Sort-Object LastWriteTime -Descending|Select-Object -First 1);if($c){$r=$c.FullName;break}};if($r){break}}};if(-not $r){Add-Type -AssemblyName System.Windows.Forms;$g=New-Object System.Windows.Forms.OpenFileDialog;$g.Title='Onde esta o pacote do Radioterapia.ai Local Suite?';$g.Filter='Pacote do Radioterapia.ai Local Suite|RADIOTERAPIA_AI_LOCAL_SUITE_*.zip;AUTO_CONTORNO*.zip|Arquivos .zip|*.zip';$g.InitialDirectory=(Join-Path $env:USERPROFILE 'Downloads');if($g.ShowDialog() -eq 'OK'){$r=$g.FileName}};if($r){Set-Content -LiteralPath $env:RADAI_SAIDA -Value $r -Encoding ASCII}"
if not exist "%RESP%" goto :sem_pacote
set "ZIP="
set /p ZIP=<"%RESP%"
del /q "%RESP%" 2>nul
if not defined ZIP goto :sem_pacote
if not exist "%ZIP%" goto :sem_pacote

echo   package: %ZIP%
echo   Extracting to %CASA%
echo.
if exist "%CASA%\" rmdir /s /q "%CASA%" 2>nul
if not exist "%CASA%" mkdir "%CASA%" 2>nul
if not exist "%CASA%" (
  echo   ERROR: could not create
  echo     "%CASA%"
  echo   Extract the .zip by hand and click START_HERE.cmd in there.
  echo.
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; try { Expand-Archive -LiteralPath '%ZIP%' -DestinationPath '%CASA%' -Force -ErrorAction Stop } catch { exit 1 }"
call :achar_sub "%CASA%"
set "SUB_CASA=%SUB%"
if not exist "%CASA%\%SUB_CASA%packager\prepare.ps1" (
  echo.
  echo   ============================================================
  echo    THE EXTRACTION DID NOT FINISH
  echo   ============================================================
  echo.
  echo    Extract the .zip by hand - right-click, "Extract All..." - and
  echo    click START_HERE.cmd in the extracted folder.
  echo   ============================================================
  echo.
  pause
  exit /b 1
)
goto :rodar

:sem_pacote
echo.
echo   ============================================================
echo    PACKAGE NOT FOUND
echo   ============================================================
echo.
echo    You clicked this file from INSIDE the .zip, and I could not
echo    locate the .zip - not by asking Windows, not by searching,
echo    not with the file picker.
echo.
echo    THE SHORT WAY:
echo      1. Close this window
echo      2. Right-click the .zip package
echo      3. Choose "Extract All..."
echo      4. Open the extracted folder and click START_HERE.cmd
echo   ============================================================
echo.
pause
exit /b 1

:rodar
set "TAMANHO="
if exist "%CASA%\PACKAGE_SIZE.txt" set /p TAMANHO=<"%CASA%\PACKAGE_SIZE.txt"
if not defined TAMANHO set "TAMANHO=20"

set "LOGDIR=%LOCALAPPDATA%\RadioterapiaAI\logs"
if "%LOCALAPPDATA%"=="" set "LOGDIR=%USERPROFILE%\RadioterapiaAI\logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%" 2>nul
if not exist "%LOGDIR%" set "LOGDIR=%TEMP%"
set "STAMP="
for /f "usebackq delims=" %%T in (`powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"`) do set "STAMP=%%T"
if not defined STAMP set "STAMP=%RANDOM%%RANDOM%"
set "RADAI_LOG_PREPARADOR=%LOGDIR%\preparer_%STAMP%.log"
>> "%RADAI_LOG_PREPARADOR%" echo START_HERE.cmd started %DATE% %TIME%
>> "%RADAI_LOG_PREPARADOR%" echo preparer: %CASA%\%SUB_CASA%packager\prepare.ps1
>> "%RADAI_LOG_PREPARADOR%" echo package size shown: about %TAMANHO% GB
set "RADAI_AJUDA_LOG=%CASA%\%SUB_CASA%packager\preparer_log.ps1"
if exist "%RADAI_AJUDA_LOG%" powershell -NoProfile -ExecutionPolicy Bypass -File "%RADAI_AJUDA_LOG%" -Modo Podar >nul 2>&1

echo   Opening the preparer...
echo.
echo   There you choose what to do:
echo.
echo     INSTALL / UPDATE APP ON THIS MACHINE, the big button. It checks
echo       whether the program is already here. If it is not, it installs
echo       everything straight into the final folder, in one step. If it
echo       is, it swaps only the code when it can, and downloads or asks
echo       for a package when not.
echo     OFFLINE MACHINE: INSTALL FROM A PACKAGE I BROUGHT, a .zip.
echo       Downloads nothing, needs no internet.
echo     MACHINE WITH INTERNET: BUILD A PACKAGE TO TAKE TO THE OFFLINE
echo       MACHINE. Downloads Python, the libraries and every model
echo       weight, and the package is about %TAMANHO% GB. Needs internet
echo       and hours.
echo     UNINSTALL.
echo.
echo   The preparer log is kept at
echo     %RADAI_LOG_PREPARADOR%
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%CASA%\%SUB_CASA%packager\minimize.ps1" >nul 2>&1
powershell -NoProfile -ExecutionPolicy Bypass -STA -File "%CASA%\%SUB_CASA%packager\prepare.ps1" >> "%RADAI_LOG_PREPARADOR%" 2>&1
set "RC=%ERRORLEVEL%"
>> "%RADAI_LOG_PREPARADOR%" echo START_HERE.cmd: the preparer exited with code %RC% at %DATE% %TIME%

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
  echo   script, read README.txt in
  echo     "%CASA%"
  echo   There is a path that does not need scripts to be unblocked.
  echo   ============================================================
)

echo.
pause
endlocal & exit /b %RC%


:achar_sub
set "SUB="
set "RADAI_P1=%~1\packager\prepare.ps1"
set "RADAI_P2=%~1\programa\packager\prepare.ps1"
if not exist "%RADAI_P1%" (
  if exist "%RADAI_P2%" set "SUB=programa\"
  goto :eof
)
if not exist "%RADAI_P2%" goto :eof
for /f "usebackq delims=" %%R in (`powershell -NoProfile -Command "if((Get-Item -LiteralPath $env:RADAI_P2).LastWriteTime -gt (Get-Item -LiteralPath $env:RADAI_P1).LastWriteTime){'programa\'}"`) do set "SUB=%%R"
goto :eof
