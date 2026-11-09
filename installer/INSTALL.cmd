@echo off
setlocal

set "PROG="
for /d %%D in ("%~dp0*") do if exist "%%~fD\radai_watcher.py" set "PROG=%%~nxD"
if defined PROG goto :pacote_ok

echo.
echo   Nao achei a pasta do programa ao lado deste arquivo.
echo   Isso acontece quando se clica de DENTRO do .zip.
echo.
echo   Procurando o pacote...
echo   Se eu nao achar sozinho, vou abrir uma janela pedindo que voce
echo   aponte o .zip.
echo.
set "RESP=%TEMP%\radai_inst_zip.txt"
if exist "%RESP%" del /q "%RESP%"
set "RADAI_SAIDA=%RESP%"
powershell -NoProfile -ExecutionPolicy Bypass -STA -Command "$ErrorActionPreference='SilentlyContinue';$n='RADIOTERAPIA_AI_LOCAL_SUITE_BUNDLE_v*.zip','RADIOTERAPIA_AI_LOCAL_SUITE_*.zip','AUTO_CONTORNO*.zip';$r=$null;try{$sh=New-Object -ComObject Shell.Application;foreach($w in $sh.Windows()){try{$p=$w.Document.Folder.Self.Path;if($p -and $p.ToLower().EndsWith('.zip') -and (Test-Path -LiteralPath $p)){$r=$p;break}}catch{}}}catch{};if(-not $r){$alvos=@();foreach($s in 'Downloads','Desktop','Documents'){$alvos+=(Join-Path $env:USERPROFILE $s)};$alvos+=$env:USERPROFILE;foreach($d in (Get-PSDrive -PSProvider FileSystem)){$alvos+=$d.Root};foreach($a in $alvos){foreach($f in $n){$c=(Get-ChildItem -Path (Join-Path $a $f) -File -EA SilentlyContinue|Sort-Object LastWriteTime -Descending|Select-Object -First 1);if($c){$r=$c.FullName;break}}; if($r){break}}};if(-not $r){Add-Type -AssemblyName System.Windows.Forms;$g=New-Object System.Windows.Forms.OpenFileDialog;$g.Title='Onde esta o pacote (.zip)?';$g.Filter='Pacote do Radioterapia.ai Local Suite|RADIOTERAPIA_AI_LOCAL_SUITE_*.zip;AUTO_CONTORNO*.zip|Arquivos .zip|*.zip';$g.InitialDirectory=(Join-Path $env:USERPROFILE 'Downloads');if($g.ShowDialog() -eq 'OK'){$r=$g.FileName}};if($r){Set-Content -LiteralPath $env:RADAI_SAIDA -Value $r -Encoding ASCII}"
if not exist "%RESP%" goto :zip_nao_achado
goto :zip_achado

:extracao_falhou
echo.
echo   ============================================================
echo    A EXTRACAO NAO COMPLETOU
echo   ============================================================
echo.
echo    A mensagem acima diz o motivo. As causas comuns sao disco
echo    cheio e antivirus segurando arquivo no meio da extracao.
echo.
echo    O caminho curto: extraia o .zip a mao, num disco com espaco,
echo    e clique no INSTALL.cmd de dentro da pasta extraida.
echo   ============================================================
echo.
pause
exit /b 1

:zip_achado
set "ZIPI="
set /p ZIPI=<"%RESP%"
del /q "%RESP%" 2>nul
if not defined ZIPI goto :zip_nao_achado
if not exist "%ZIPI%" goto :zip_nao_achado

echo   pacote: %ZIPI%
set "RESPX=%TEMP%\radai_inst_extrai.txt"
if exist "%RESPX%" del /q "%RESPX%"
set "RADAI_ZIP=%ZIPI%"
set "RADAI_SAIDA=%RESPX%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop';Add-Type -AssemblyName System.IO.Compression.FileSystem;$z=$env:RADAI_ZIP;try{$a=[System.IO.Compression.ZipFile]::OpenRead($z);$itens=@($a.Entries|Where-Object{$_.Name});$quantos=$itens.Count;$precisa=[int64](($itens|Measure-Object -Property Length -Sum).Sum*1.05);$a.Dispose()}catch{Write-Host ('   nao consegui ler o .zip: '+$_.Exception.Message);exit 1};$cand=@();try{$dz=[System.IO.Path]::GetPathRoot($z);if($dz){$dd=New-Object System.IO.DriveInfo($dz);if($dd.IsReady -and $dd.DriveType -eq 'Fixed'){$cand+=$dd}}}catch{};foreach($d in [System.IO.DriveInfo]::GetDrives()){try{if($d.IsReady -and $d.DriveType -eq 'Fixed'){$cand+=$d}}catch{}};$cand=$cand|Sort-Object @{e={$_.RootDirectory.FullName -eq [System.IO.Path]::GetPathRoot($z)};d=$true},@{e={$_.AvailableFreeSpace};d=$true};$alvo=$null;foreach($d in $cand){if($d.AvailableFreeSpace -gt $precisa){$alvo=(Join-Path $d.RootDirectory.FullName 'radai_pacote_extraido');break}};if(-not $alvo){Write-Host ('   NAO CABE em disco nenhum: o pacote precisa de '+[math]::Round($precisa/1GB,1)+' GB.');foreach($d in $cand){Write-Host ('     '+$d.Name+'  livre '+[math]::Round($d.AvailableFreeSpace/1GB,1)+' GB')};exit 2};Write-Host ('   extraindo para '+$alvo);Write-Host ('   '+$quantos+' arquivos, '+[math]::Round($precisa/1GB,1)+' GB. Pode demorar alguns minutos.');if(Test-Path -LiteralPath $alvo){Remove-Item -LiteralPath $alvo -Recurse -Force -EA SilentlyContinue};try{[System.IO.Compression.ZipFile]::ExtractToDirectory($z,$alvo)}catch{Write-Host ('   a extracao parou: '+$_.Exception.Message);exit 3};$saiu=@(Get-ChildItem -LiteralPath $alvo -Recurse -File -EA SilentlyContinue).Count;if($saiu -lt $quantos){Write-Host ('   extracao INCOMPLETA: '+$saiu+' de '+$quantos+' arquivos.');exit 4};Write-Host ('   extraido: '+$saiu+' arquivos');Set-Content -LiteralPath $env:RADAI_SAIDA -Value $alvo -Encoding ASCII"
set "EXTRAI="
if exist "%RESPX%" set /p EXTRAI=<"%RESPX%"
if exist "%RESPX%" del /q "%RESPX%"
if not defined EXTRAI goto :extracao_falhou
if not exist "%EXTRAI%\INSTALL.cmd" goto :extracao_falhou
echo   Extraido. Continuando a instalacao de la...
echo.
call "%EXTRAI%\INSTALL.cmd"
set "RCZ=%ERRORLEVEL%"
rmdir /s /q "%EXTRAI%" 2>nul
exit /b %RCZ%

:zip_nao_achado
echo.
echo   ============================================================
echo    NAO ACHEI O PACOTE
echo   ============================================================
echo.
echo    Voce clicou neste arquivo de DENTRO do .zip, e eu nao
echo    consegui localizar o .zip sozinho.
echo.
echo    O CAMINHO CURTO:
echo      1. Feche esta janela
echo      2. Clique com o botao direito no .zip do pacote
echo      3. Escolha "Extrair tudo..."
echo      4. Abra a pasta extraida e clique no INSTALL.cmd de la
echo   ============================================================
echo.
pause
exit /b 1

:pacote_ok
set "AQUI=%~dp0"
set "PS1=%AQUI%INSTALL.ps1"

echo.
echo ============================================================
echo   Radioterapia.AI - instalador
echo ============================================================
echo.

where powershell >nul 2>&1
if errorlevel 1 (
  echo   PAROU: este computador nao tem PowerShell.
  echo.
  echo   O instalador precisa dele. Avise quem administra esta instalacao.
  echo.
  pause
  exit /b 1
)

if not exist "%PS1%" (
  echo   PAROU: nao achei o INSTALL.ps1 nesta pasta:
  echo   "%AQUI%"
  echo.
  echo   Isso quase sempre significa que o .zip foi extraido pela
  echo   metade, ou que voce esta rodando de DENTRO do .zip.
  echo.
  echo   O QUE FAZER: botao direito no .zip, "Extrair tudo...",
  echo   e rode o INSTALL.cmd de dentro da pasta extraida.
  echo.
  pause
  exit /b 1
)

set "RADAI_PASTA_PACOTE=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-Content -LiteralPath '%PS1%' -Raw -Encoding UTF8 | Invoke-Expression"
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" goto :fim
if "%RC%"=="2" (
  echo   Instalacao cancelada. Nada foi alterado.
  echo.
  pause
  exit /b 2
)
echo ============================================================
echo   A INSTALACAO NAO TERMINOU ^(codigo %RC%^).
echo   A mensagem acima diz o motivo.
echo   Log: %AQUI%INSTALL_LOG.txt
echo ============================================================
echo.
pause
exit /b %RC%

:fim
pause
exit /b 0
