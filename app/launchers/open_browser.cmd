@echo off
setlocal
set "URL=%~1"
if "%URL%"=="" set "URL=http://127.0.0.1:8777/"

set "PERFIL=%TEMP%\radai_janela"

set "PORTA=8777"
for /f "tokens=3 delims=:/" %%P in ("%URL%") do set "PORTA=%%P"
set "PORTA=%PORTA:/=%"
if not defined PORTA set "PORTA=8777"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$fim=(Get-Date).AddSeconds(60); while((Get-Date) -lt $fim){ try{ $c=New-Object Net.Sockets.TcpClient; $c.Connect('127.0.0.1',%PORTA%); $c.Close(); exit 0 } catch { Start-Sleep -Milliseconds 500 } }; exit 1" >nul 2>&1

REM GUARDA: o Windows 10 LTSB (build 14393) nao traz o Edge; o recuo tenta
REM o Chrome e depois o navegador padrao.
set "EDGE=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if not exist "%EDGE%" set "EDGE=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
if exist "%EDGE%" (
  start "" "%EDGE%" --app=%URL% --start-maximized --user-data-dir="%PERFIL%"
  exit /b 0
)

set "CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" set "CHROME=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if exist "%CHROME%" (
  start "" "%CHROME%" --app=%URL% --start-maximized --user-data-dir="%PERFIL%"
  exit /b 0
)

echo.
echo   ==============================================================
echo    NEM O EDGE NEM O CHROME FORAM ENCONTRADOS NESTA ESTACAO.
echo.
echo    O ContourLab precisa de um dos dois. Vou abrir o navegador
echo    padrao; se ele for o Internet Explorer, a propria tela vai
echo    dizer isso -- nenhuma parte do programa funciona nele.
echo.
echo    Endereco:  %URL%
echo   ==============================================================
echo.
start "" %URL%
REM GUARDA: chamado na janela do lancador, que fecha logo depois.
timeout /t 20 >nul 2>&1
exit /b 0
