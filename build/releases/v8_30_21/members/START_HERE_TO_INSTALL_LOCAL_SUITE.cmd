@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "PSModulePath="
set "RADAI_SETUP_PRODUCT=local-suite"
set "RADAI_SETUP_VERSION=8.30.21"
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
  "$p.Title='Locate the original Local Suite ZIP';$p.Filter='ZIP archives (*.zip)|*.zip';$p.CheckFileExists=$true;$p.Multiselect=$false;" ^
  "try {if($p.ShowDialog() -eq [Windows.Forms.DialogResult]::OK){return $p.FileName}} finally {$p.Dispose()}" ^
  "}" ^
  "function SafePath($name) {" ^
  "$name=$name.Replace('\','/').TrimEnd('/');" ^
  "if(-not $name -or [IO.Path]::IsPathRooted($name) -or $name -match '[\x00-\x1f\x22<>:|?*]'){throw 'Invalid archive path.'};" ^
  "foreach($part in $name.Split('/')){if($part -in @('','.','..') -or $part.EndsWith('.') -or $part.EndsWith(' ') -or $part -match '^(?i:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)'){throw 'Invalid archive path.'}};" ^
  "$target=[IO.Path]::GetFullPath((Join-Path $dst $name));if(-not $target.StartsWith($dst+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Archive path escapes extraction folder.'};return $target" ^
  "}" ^
  "function SetupEntry($entries) {" ^
  "$tops=@($entries.Keys -like '*/*'|ForEach-Object{$_.Split('/')[0]}|Select-Object -Unique);$roots=@('');if($tops.Count -eq 1){$roots+=($tops[0]+'/')};" ^
  "foreach($root in $roots){foreach($dir in '','programa/'){$prefix=$root+$dir;$file=$prefix+'packager/prepare.ps1';$e=$entries[$prefix+'entrega.txt'];" ^
  "if(!$entries[$file] -or !$e -or $e.Length -gt 8192){continue};$r=[IO.StreamReader]::new($e.Open());try{$raw=$r.ReadToEnd()}finally{$r.Dispose()};" ^
  "if($raw -match '(?m)^PROJETO=LOCAL_SUITE\s*$' -and $raw -match '(?m)^VERSAO=([\d.]+)\s*$' -and $Matches[1] -eq $env:RADAI_SETUP_VERSION){return $file}}}" ^
  "}" ^
  "function Explorer-Zips {" ^
  "try{$shell=New-Object -ComObject Shell.Application;foreach($w in $shell.Windows()){try{$w.Document.Folder.Self.Path;foreach($i in $w.Document.SelectedItems()){$i.Path}}catch{}}}catch{}" ^
  "}" ^
  "function Find-InstallerZip {" ^
  "$self=$env:RADAI_SETUP_LAUNCHER;if(-not [IO.File]::Exists($self)){return};$paths=@(Explorer-Zips);$seen=@{};" ^
  "$hint=if($self -match '(?:Temp\d+_|[\da-f-]{36}_)([^\\]+?\.zip)(?:\.[^\\]+)?\\'){$Matches[1]};" ^
  "try{foreach($line in (Get-Content -LiteralPath $self -Stream Zone.Identifier -ErrorAction Stop)){if($line -match '^(?:HostUrl|ReferrerUrl)=(file:.+)$'){$paths+=([uri]$Matches[1]).LocalPath}}}catch{};" ^
  "$key=[Microsoft.Win32.Registry]::CurrentUser.OpenSubKey('Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders');" ^
  "$downloads=if($key){try{$key.GetValue('{374DE290-123F-4565-9164-39C4925E467B}')}finally{$key.Dispose()}};" ^
  "if(-not $downloads){$downloads=Join-Path $env:USERPROFILE 'Downloads'};" ^
  "$dirs=@([Environment]::ExpandEnvironmentVariables($downloads),[Environment]::GetFolderPath('DesktopDirectory'),[Environment]::GetFolderPath('MyDocuments'),[Environment]::CurrentDirectory);" ^
  "$base='RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_';foreach($name in @($hint,($base+'v'+$env:RADAI_SETUP_VERSION+'.zip'),($base+'LATEST.zip'))){if(!$name){continue};" ^
  "try{$recent=[Environment]::GetFolderPath('Recent');$ws=New-Object -ComObject WScript.Shell;foreach($ln in @($name,[IO.Path]::GetFileNameWithoutExtension($name))){$link=Join-Path $recent ($ln+'.lnk');if([IO.File]::Exists($link)){$paths+=$ws.CreateShortcut($link).TargetPath}}}catch{};foreach($dir in $dirs){if($dir){$paths+=Join-Path $dir $name}}};" ^
  "$sha=[Security.Cryptography.SHA256]::Create();try{$digest=[Convert]::ToBase64String($sha.ComputeHash([IO.File]::ReadAllBytes($self)));" ^
  "foreach($item in $paths){if($item -notmatch '^(.+?\.zip)(?:[\\/]|$)'){continue};$path=$Matches[1];" ^
  "if($seen.ContainsKey($path) -or -not [IO.File]::Exists($path)){continue};$seen[$path]=1;$probe=$null;$keep=$false;try{" ^
  "$probe=[IO.Compression.ZipFile]::OpenRead($path);if($probe.Entries.Count -gt 20000){continue};$launch=@($probe.Entries|Where-Object{$_.FullName.Replace('\','/') -match '^(?:[^/]+/)?START_HERE_TO_INSTALL_LOCAL_SUITE\.cmd$'});" ^
  "if($launch.Count -ne 1 -or $launch[0].Length -ne (Get-Item -LiteralPath $self).Length){continue};$stream=$launch[0].Open();try{$match=$digest -ceq [Convert]::ToBase64String($sha.ComputeHash($stream))}finally{$stream.Dispose()};" ^
  "if($match){$map=@{};foreach($e in $probe.Entries){$map[$e.FullName.Replace('\','/')]=$e};if(!(SetupEntry $map)){continue};$keep=$true;return @{Path=$path;Zip=$probe}}}catch{}finally{if($probe -and -not $keep){$probe.Dispose()}}}}finally{$sha.Dispose()}" ^
  "}" ^
  "try {" ^
  "Add-Type -AssemblyName System.IO.Compression.FileSystem;" ^
  "$located=Find-InstallerZip;" ^
  "if($located){$archive=$located.Path;$z=$located.Zip}else{" ^
  "$archive=Select-InstallerZip;if(-not $archive){Write-Host 'Setup canceled.';exit 0};$z=[IO.Compression.ZipFile]::OpenRead($archive)};" ^
  "$dst=[IO.Path]::Combine([IO.Path]::GetTempPath(),('RadioterapiaAI-'+$env:RADAI_SETUP_PRODUCT+'-setup-'+[guid]::NewGuid().ToString('N')));" ^
  "try {" ^
  "if($z.Entries.Count -gt 20000){throw 'Too many files in archive.'};$entries=@{};$total=0L;" ^
  "foreach($e in $z.Entries){$name=$e.FullName.Replace('\','/');[void](SafePath $name);$key=$name.TrimEnd('/');if($entries.ContainsKey($key) -or (($e.ExternalAttributes -shr 16) -band 61440) -eq 40960){throw 'Duplicate paths or links are not allowed.'};$entries[$key]=$e;$total+=$e.Length;if($total -gt 68719476736L){throw 'Archive exceeds the allowed size.'}};" ^
  "$setup=SetupEntry $entries;if(!$setup){throw ('This ZIP is not the selected installer. Expected Local Suite '+$env:RADAI_SETUP_VERSION+'.')};" ^
  "$drive=New-Object IO.DriveInfo([IO.Path]::GetPathRoot($dst));if($drive.AvailableFreeSpace -lt ($total+268435456L)){throw 'Not enough disk space to extract the package.'};" ^
  "[void][IO.Directory]::CreateDirectory($dst);Write-Host ('Extracting: '+$archive);$count=0;" ^
  "foreach($e in $z.Entries){if($e.FullName.Replace('\','/').EndsWith('/')){continue};$target=SafePath $e.FullName;[void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($target));$incoming=$e.Open();$output=New-Object IO.FileStream($target,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write);" ^
  "try{$buffer=New-Object byte[] 1048576;$copied=0L;while(($length=$incoming.Read($buffer,0,$buffer.Length)) -gt 0){$copied+=$length;if($copied -gt $e.Length){throw 'Archive entry exceeds its declared size.'};$output.Write($buffer,0,$length)};if($copied -ne $e.Length){throw 'Truncated archive entry.'}}finally{$output.Dispose();$incoming.Dispose()};$count++;Write-Progress -Activity 'Extracting Local Suite' -Status ($count.ToString()+' files')};" ^
  "Write-Progress -Activity 'Extracting Local Suite' -Completed;$entry=SafePath $setup" ^
  "} finally {$z.Dispose()};" ^
  "if(-not [IO.File]::Exists($entry)){throw 'The extracted setup is incomplete.'};" ^
  "Write-Host 'Opening Local Suite...';$ErrorActionPreference='Continue';" ^
  "& $env:RADAI_SETUP_POWERSHELL -NoLogo -NoProfile -ExecutionPolicy Bypass -STA -File $entry;exit $LASTEXITCODE" ^
  "} catch {Write-Host ('Setup stopped: '+$_.Exception.Message) -ForegroundColor Yellow;exit 1}"
set "RADAI_SETUP_RC=%ERRORLEVEL%"
goto :finished
:install
"%RADAI_SETUP_POWERSHELL%" -NoLogo -NoProfile -ExecutionPolicy Bypass -STA -File "%RADAI_SETUP_ENTRY%"
set "RADAI_SETUP_RC=%ERRORLEVEL%"
:finished
if not "%RADAI_SETUP_RC%"=="0" set /p "RADAI_CLOSE=Press Enter to close..."
exit /b %RADAI_SETUP_RC%
