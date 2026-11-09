@echo off
setlocal
cd /d "%~dp0.."


set "PY="
if exist "%~dp0..\.venv\Scripts\python.exe" set "PY=%~dp0..\.venv\Scripts\python.exe"
if not defined PY (
  where python >nul 2>&1
  if not errorlevel 1 set "PY=python"
)
if not defined PY (
  echo ERRO: preciso de um Python nesta maquina para montar o pacote.
  echo       ^(so a MAQUINA DE MONTAGEM precisa; a estacao nao.^)
  echo.
  pause
  exit /b 1
)

echo ============================================================
echo   Configurador do Ambiente - Radioterapia.AI
echo ============================================================
echo   Isso baixa varios GB e demora. Deixe a janela aberta.
echo ============================================================
echo.

"%PY%" "%~dp0configurar_ambiente.py" %*
set "RC=%ERRORLEVEL%"

echo.
if not "%RC%"=="0" (
  echo ============================================================
  echo   FALHOU ^(codigo %RC%^).
  echo   O log fica na oficina: _montagem\configurar_ambiente_log.txt
  echo   Da para retomar de onde parou: veja a etapa no fim do log
  echo   e rode  CONFIGURAR_AMBIENTE.cmd --etapas N
  echo ============================================================
) else (
  echo ============================================================
  echo   PRONTO. O empacotador imprimiu acima a pasta de saida,
  echo   dentro de _montagem\. Ela NAO e entrega: a entrega e o
  echo   instalador leve, na raiz de entrega.
  echo ============================================================
)
echo.
pause
exit /b %RC%
