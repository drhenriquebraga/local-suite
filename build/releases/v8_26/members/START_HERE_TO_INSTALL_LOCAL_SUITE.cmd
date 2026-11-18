@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "RADAI_SETUP_PRODUCT=local-suite"
set "RADAI_SETUP_RELATIVE=packager\prepare.ps1"
set "RADAI_SETUP_POWERSHELL=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
set "RADAI_SETUP_LAUNCHER=%~f0"
set "RADAI_SETUP_ENTRY="
if exist "%~dp0programa\packager\prepare.ps1" set "RADAI_SETUP_ENTRY=%~dp0programa\packager\prepare.ps1"
if not defined RADAI_SETUP_ENTRY if exist "%~dp0packager\prepare.ps1" set "RADAI_SETUP_ENTRY=%~dp0packager\prepare.ps1"
if not defined RADAI_SETUP_ENTRY if exist "%~dp0prepare.ps1" set "RADAI_SETUP_ENTRY=%~dp0prepare.ps1"
echo.
echo   Local Suite
echo   ============================
echo.
if defined RADAI_SETUP_ENTRY goto :install
rem ZIP recovery: a literal PowerShell command, never the contents of this CMD.
"%RADAI_SETUP_POWERSHELL%" -NoLogo -NoProfile -ExecutionPolicy Bypass -STA -Command ^
  "$ErrorActionPreference='Stop';" ^
  "function Select-InstallerZip {" ^
  "Add-Type -AssemblyName System.Windows.Forms;" ^
  "$p=New-Object Windows.Forms.OpenFileDialog;" ^
  "$p.Title='Selecione o ZIP completo / Select the complete ZIP';$p.Filter='ZIP (*.zip)|*.zip';$p.CheckFileExists=$true;$p.Multiselect=$false;" ^
  "try {if($p.ShowDialog() -eq [Windows.Forms.DialogResult]::OK){return $p.FileName}} finally {$p.Dispose()}" ^
  "}" ^
  "function SafePath($name) {" ^
  "$name=$name.Replace('\','/').TrimEnd('/');" ^
  "if(-not $name -or [IO.Path]::IsPathRooted($name) -or $name -match '[\x00-\x1f\x22<>:|?*]'){throw 'Invalid archive path.'};" ^
  "foreach($part in $name.Split('/')){if($part -in @('','.','..') -or $part.EndsWith('.') -or $part.EndsWith(' ') -or $part -match '^(?i:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)'){throw 'Invalid archive path.'}};" ^
  "$target=[IO.Path]::GetFullPath((Join-Path $dst $name));if(-not $target.StartsWith($dst+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Archive path escapes extraction folder.'};return $target" ^
  "}" ^
  "function ReadMetadata($name) {" ^
  "$e=$entries[$name];if(-not $e -or $e.Length -gt 8388608){return $null};" ^
  "$r=New-Object IO.StreamReader($e.Open(),[Text.Encoding]::UTF8,$true);try{return $r.ReadToEnd()}finally{$r.Dispose()}" ^
  "}" ^
  "function Find-InstallerZip {" ^
  "$temp=[IO.Path]::GetTempPath();$self=$env:RADAI_SETUP_LAUNCHER;" ^
  "if(-not $self -or -not $self.StartsWith($temp,[StringComparison]::OrdinalIgnoreCase) -or $self.Substring($temp.Length) -notmatch '^Temp[0-9]+_([^\\]+\.zip)\\'){return};" ^
  "$name=$Matches[1];$probe=$null;$keep=$false;try {" ^
  "$key=[Microsoft.Win32.Registry]::CurrentUser.OpenSubKey('Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders');$downloads=if($key){try{$key.GetValue('{374DE290-123F-4565-9164-39C4925E467B}')}finally{$key.Dispose()}};" ^
  "if(-not $downloads){$downloads=Join-Path $env:USERPROFILE 'Downloads'};" ^
  "$path=[IO.Path]::Combine([Environment]::ExpandEnvironmentVariables($downloads),$name);if(-not [IO.File]::Exists($path)){return};" ^
  "$probe=[IO.Compression.ZipFile]::OpenRead($path);if($probe.Entries.Count -gt 20000){return};" ^
  "$launch=@($probe.Entries|Where-Object{$_.FullName.Replace('\','/') -match '^(?:[^/]+/)?START_HERE_TO_INSTALL_LOCAL_SUITE\.cmd$'});" ^
  "if($launch.Count -ne 1){return};$local=[IO.File]::OpenRead($self);try {" ^
  "if($launch[0].Length -ne $local.Length){return};$stream=$launch[0].Open();$sha=[Security.Cryptography.SHA256]::Create();" ^
  "try{$match=[Convert]::ToBase64String($sha.ComputeHash($stream)) -ceq [Convert]::ToBase64String($sha.ComputeHash($local))}finally{$stream.Dispose();$sha.Dispose()};" ^
  "if($match){$keep=$true;return @{Path=$path;Zip=$probe}}}finally{$local.Dispose()}" ^
  "} catch {} finally {if($probe -and -not $keep){$probe.Dispose()}}" ^
  "}" ^
  "try {" ^
  "Add-Type -AssemblyName System.IO.Compression.FileSystem;" ^
  "$located=Find-InstallerZip;" ^
  "if($located){$archive=$located.Path;$z=$located.Zip;Write-Host 'ZIP localizado em Downloads / ZIP found in Downloads.'}else{" ^
  "Write-Host 'Selecione o ZIP completo para extrair / Select the complete ZIP to extract.';" ^
  "$archive=Select-InstallerZip;if(-not $archive){Write-Host 'Cancelado / Cancelled. Nenhuma instalacao iniciada.';exit 0};$z=[IO.Compression.ZipFile]::OpenRead($archive)};" ^
  "$dst=[IO.Path]::Combine([IO.Path]::GetTempPath(),('RadioterapiaAI-'+$env:RADAI_SETUP_PRODUCT+'-setup-'+[guid]::NewGuid().ToString('N')));" ^
  "try {" ^
  "if($z.Entries.Count -gt 20000){throw 'Too many files in archive.'};$entries=@{};$total=0L;" ^
  "foreach($e in $z.Entries){$name=$e.FullName.Replace('\','/');[void](SafePath $name);$key=$name.TrimEnd('/');if($entries.ContainsKey($key) -or (($e.ExternalAttributes -shr 16) -band 61440) -eq 40960){throw 'Duplicate paths or links are not allowed.'};$entries[$key]=$e;$total+=$e.Length;if($total -gt 68719476736L){throw 'Archive exceeds the allowed size.'}};" ^
  "$prefixes=@('','programa/');$tops=@($entries.Keys|Where-Object{$_.Contains('/')}|ForEach-Object{$_.Split('/')[0]}|Select-Object -Unique);if($tops.Count -eq 1){$prefixes+=($tops[0]+'/');$prefixes+=($tops[0]+'/programa/')};" ^
  "$found=$false;$relative=$env:RADAI_SETUP_RELATIVE.Replace('\','/');" ^
  "foreach($prefix in $prefixes|Select-Object -Unique){if(-not $entries.ContainsKey($prefix+$relative)){continue};$raw=ReadMetadata ($prefix+'entrega.txt');if($raw -match '(?m)^PROJETO=LOCAL_SUITE\s*$'){$found=$true;break}};" ^
  "if(-not $found){throw 'Este ZIP nao corresponde ao instalador escolhido. / This ZIP is not the selected installer.'};" ^
  "$drive=New-Object IO.DriveInfo([IO.Path]::GetPathRoot($dst));if($drive.AvailableFreeSpace -lt ($total+268435456L)){throw 'Sem espaco para extrair o pacote. / Not enough disk space to extract the package.'};" ^
  "[void][IO.Directory]::CreateDirectory($dst);Write-Host ('Extraindo / Extracting: '+$archive);$count=0;" ^
  "foreach($e in $z.Entries){if($e.FullName.Replace('\','/').EndsWith('/')){continue};$target=SafePath $e.FullName;[void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($target));$incoming=$e.Open();$output=New-Object IO.FileStream($target,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write);" ^
  "try{$buffer=New-Object byte[] 1048576;$copied=0L;while(($length=$incoming.Read($buffer,0,$buffer.Length)) -gt 0){$copied+=$length;if($copied -gt $e.Length){throw 'Archive entry exceeds its declared size.'};$output.Write($buffer,0,$length)};if($copied -ne $e.Length){throw 'Truncated archive entry.'}}finally{$output.Dispose();$incoming.Dispose()};$count++;Write-Progress -Activity 'Extraindo / Extracting' -Status ($count.ToString()+' arquivos / files')};" ^
  "Write-Progress -Activity 'Extraindo / Extracting' -Completed;$entry=SafePath ($prefix+$relative)" ^
  "} finally {$z.Dispose()};" ^
  "if(-not [IO.File]::Exists($entry)){throw 'O pacote extraido esta incompleto. / Extracted package is incomplete.'};" ^
  "Write-Host ('Abrindo / Opening '+$env:RADAI_SETUP_PRODUCT+'...');$ErrorActionPreference='Continue';" ^
  "& $env:RADAI_SETUP_POWERSHELL -NoLogo -NoProfile -ExecutionPolicy Bypass -STA -File $entry;exit $LASTEXITCODE" ^
  "} catch {Write-Host ('Instalacao interrompida / Installation stopped: '+$_.Exception.Message) -ForegroundColor Yellow;Write-Host 'O programa e os dados existentes foram preservados. / Existing application and data were preserved.';exit 1}"
set "RADAI_SETUP_RC=%ERRORLEVEL%"
goto :finished
:install
"%RADAI_SETUP_POWERSHELL%" -NoLogo -NoProfile -ExecutionPolicy Bypass -STA -File "%RADAI_SETUP_ENTRY%"
set "RADAI_SETUP_RC=%ERRORLEVEL%"
:finished
if not "%RADAI_SETUP_RC%"=="0" pause
exit /b %RADAI_SETUP_RC%
