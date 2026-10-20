@echo off
setlocal
cd /d "%~dp0"

set "BUNDLE=%~dp0_montagem\LOCAL_SUITE"
if exist "%~dp0_bundle.txt" set /p BUNDLE=<"%~dp0_bundle.txt"

if not exist "%BUNDLE%\python\python.exe" (
  echo ERRO: nao achei "%BUNDLE%\python\python.exe".
  echo.
  echo Se o bundle estiver em outro lugar, escreva o caminho da pasta
  echo LOCAL_SUITE dentro de um arquivo _bundle.txt, ao lado deste .cmd.
  echo.
  pause
  exit /b 1
)

set "TOTALSEG_WEIGHTS_PATH=%BUNDLE%\ts_weights"
set "RADAI_MODELOS_DIR=%BUNDLE%\modelos"
set "PYTHONIOENCODING=utf-8:replace"

if exist "%~dp0_dados.txt" set /p RADAI_CALIB_DIR=<"%~dp0_dados.txt"

if defined RADAI_CALIB_DIR if not defined RADAI_REGISTRO_DIR set "RADAI_REGISTRO_DIR=%RADAI_CALIB_DIR%\registro"

set "APPDEV=%BUNDLE%\..\app_dev"
"%BUNDLE%\python\python.exe" "%~dp0tools\_componentes.py" --montar "%APPDEV%"
if errorlevel 1 (
  echo ERRO: nao consegui montar o app a partir das pastas dos componentes.
  pause
  exit /b 1
)

echo ============================================================
echo  Vigia - codigo do repositorio, runtime do bundle
echo  Python: %BUNDLE%\python\python.exe
echo  Pesos:  %TOTALSEG_WEIGHTS_PATH%
echo  Modelos:%RADAI_MODELOS_DIR%
echo  App:    %APPDEV%   (montado da Suite e dos componentes)
echo  Config: %~dp0app\radai_watcher.config   (criado no primeiro uso)
echo  Painel: http://127.0.0.1:8777/   (ou a PORT do seu config)
if defined RADAI_CALIB_DIR (
  echo  Acervo: "%RADAI_CALIB_DIR%"   ^(dado de paciente^)
) else (
  echo  Acervo: "%~dp0app\calibracao"   ^(padrao - confira se sincroniza^)
)
if defined RADAI_REGISTRO_DIR (
  echo  Registro: "%RADAI_REGISTRO_DIR%"
) else (
  echo  Registro: "%~dp0app\registro"   ^(padrao - SINCRONIZA; crie o _dados.txt^)
)
echo.
echo  Telas:  /  porta   /lote  rodar agora   /ver  ver segmentacao   /config
echo ============================================================
echo.
echo  As estruturas saem como SUGESTAO NAO APROVADA (sufixo _ai).
echo  Revisao e aprovacao continuam sendo ato medico, no TPS.
echo.
echo  Deixe esta janela ABERTA. Para parar: Ctrl+C ou feche a janela.
echo.

if not defined RADAI_CONFIG set "RADAI_CONFIG=%~dp0app\radai_watcher.config"
if not defined RADAI_CALIB_DIR set "RADAI_CALIB_DIR=%~dp0app\calibracao"
if not defined RADAI_REGISTRO_DIR set "RADAI_REGISTRO_DIR=%~dp0app\registro"
start "" http://127.0.0.1:8777/
"%BUNDLE%\python\python.exe" "%APPDEV%\radai_watcher.py"
set "RC=%ERRORLEVEL%"

echo.
if not "%RC%"=="0" (
  echo ============================================================
  echo  O VIGIA PAROU com codigo %RC%.
  echo  Veja o fim de: "%APPDEV%\radai_vigia.log"
  echo  Guarde esse arquivo: a primeira excecao dele diz a causa.
  echo ============================================================
) else (
  echo Vigia encerrado.
)
echo.
pause
endlocal & exit /b %RC%
