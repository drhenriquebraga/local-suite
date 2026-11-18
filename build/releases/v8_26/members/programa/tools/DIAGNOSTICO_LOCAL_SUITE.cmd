@echo off
setlocal DisableDelayedExpansion
set "LS_DIAG_SOURCE=%~f0"
set "LS_DIAG_ROOT=%~1"
set "LS_DIAG_OUT=%~2"
set "LS_DIAG_MODE=%~3"
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -Sta -Command "$ErrorActionPreference='Stop'; $src=[IO.File]::ReadAllText($env:LS_DIAG_SOURCE,[Text.Encoding]::UTF8); $tag=[char]10+'#==LOCAL-SUITE-COLETOR=='+[char]13+[char]10; $at=$src.IndexOf($tag,[StringComparison]::Ordinal); if($at -lt 0){exit 3}; $argsColeta=@{}; if($env:LS_DIAG_ROOT){$argsColeta.InstallRoot=$env:LS_DIAG_ROOT}; if($env:LS_DIAG_OUT){$argsColeta.OutputDir=$env:LS_DIAG_OUT}; if($env:LS_DIAG_MODE -ieq '/quiet'){$argsColeta.Quiet=$true}; & ([scriptblock]::Create($src.Substring($at+$tag.Length))) @argsColeta"
exit /b %errorlevel%
#==LOCAL-SUITE-COLETOR==
[CmdletBinding()]
param(
    [string]$InstallRoot,
    [string]$OutputDir,
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$clock = [Diagnostics.Stopwatch]::StartNew()
$utf8 = New-Object Text.UTF8Encoding($false)

function Show-Message([string]$Message) {
    if (!$Quiet) {
        try {
            Add-Type -AssemblyName System.Windows.Forms
            [void][Windows.Forms.MessageBox]::Show($Message, 'Local Suite')
        } catch { [Console]::Error.WriteLine($Message) }
    }
}

function Test-LocalPath([string]$Path) {
    if (!$Path -or $Path -notmatch '^[a-zA-Z]:[\\/]') { return $false }
    $drive = [IO.DriveInfo]::new([IO.Path]::GetPathRoot($Path))
    return $drive.DriveType -in @('Fixed','Removable','Ram')
}

function Test-PlainPath([string]$Path) {
    # GUARDA: nunca segue junctions/symlinks, inclusive em ancestrais.
    try {
        $full = [IO.Path]::GetFullPath($Path)
        if (!(Test-LocalPath $full)) { return $false }
        $root = [IO.Path]::GetPathRoot($full)
        $at = $root
        foreach ($part in $full.Substring($root.Length).Split('\')) {
            if (!$part) { continue }
            $at = [IO.Path]::Combine($at, $part)
            if (([IO.File]::GetAttributes($at) -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                return $false
            }
        }
        return $true
    } catch { return $false }
}

function Read-BoundedText([string]$Path, [int]$Limit, [switch]$Tail) {
    if (!(Test-PlainPath $Path)) { return $null }
    $stream = $null
    try {
        $stream = [IO.File]::Open($Path, 'Open', 'Read', [IO.FileShare]7)
        $size = $stream.Length
        if ($size -gt $Limit -and !$Tail) { return $null }
        $count = [int][Math]::Min([long]$Limit, $size)
        if ($size -gt $count) { [void]$stream.Seek(-$count, 'End') }
        $bytes = New-Object byte[] $count
        $used = 0
        while ($used -lt $count) {
            $got = $stream.Read($bytes, $used, $count - $used)
            if (!$got) { break }
            $used += $got
        }
        $s = $utf8.GetString($bytes, 0, $used).TrimStart([char]0xFEFF)
        if ($size -gt $count) {
            $newline = $s.IndexOf([char]10)
            if ($newline -lt 0) { return '' }
            return $s.Substring($newline + 1)
        }
        return $s
    } catch { return $null } finally { if ($stream) { $stream.Dispose() } }
}

function Read-Object([string]$Path) {
    try {
        $raw = Read-BoundedText $Path 131072
        if ($raw) { return ConvertFrom-Json -InputObject $raw -ErrorAction Stop }
    } catch {}
}

function Get-VersionValue($Value, [switch]$Package) {
    if ($Value -isnot [string]) { return $null }
    $pattern = '\A\d{1,2}\.\d{1,3}(?:\.\d{1,4})?\z'
    if ($Package) { $pattern = '\A\d{1,2}\.\d{1,3}(?:\.\d{1,6}){0,2}(?:\+(?:cu\d{2,4}|cpu))?\z' }
    if ($Value -cmatch $pattern) { return $Value }
    return $null
}

function Get-CountValue($Value) {
    if (($Value -is [int] -or $Value -is [long]) -and $Value -ge 0 -and $Value -le 2147483647) {
        return [long]$Value
    }
    return $null
}

function Get-MemorySnapshot {
    $r = [ordered]@{source='unavailable'; physical_total_mib=$null; available_mib=$null;
        committed_mib=$null; commit_limit_mib=$null; commit_peak_mib=$null; commit_free_mib=$null}
    try {
        if (!('LocalSuiteDiagnostics.Perf' -as [type])) {
            Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
namespace LocalSuiteDiagnostics {
    [StructLayout(LayoutKind.Sequential)]
    public struct PerformanceInfo {
        public uint Size;
        public UIntPtr CommitTotal, CommitLimit, CommitPeak, PhysicalTotal, PhysicalAvailable;
        public UIntPtr SystemCache, KernelTotal, KernelPaged, KernelNonpaged, PageSize;
        public uint HandleCount, ProcessCount, ThreadCount;
    }
    public static class Perf {
        [DllImport("psapi.dll", SetLastError=true)]
        public static extern bool GetPerformanceInfo(out PerformanceInfo value, uint size);
    }
}
'@
        }
        $info = New-Object LocalSuiteDiagnostics.PerformanceInfo
        if (![LocalSuiteDiagnostics.Perf]::GetPerformanceInfo([ref]$info, [Runtime.InteropServices.Marshal]::SizeOf($info))) { throw 'perf' }
        $page = $info.PageSize.ToUInt64()
        $r.physical_total_mib = [long][Math]::Floor(($info.PhysicalTotal.ToUInt64() * $page) / 1MB)
        $r.available_mib = [long][Math]::Floor(($info.PhysicalAvailable.ToUInt64() * $page) / 1MB)
        $r.committed_mib = [long][Math]::Floor(($info.CommitTotal.ToUInt64() * $page) / 1MB)
        $r.commit_limit_mib = [long][Math]::Floor(($info.CommitLimit.ToUInt64() * $page) / 1MB)
        $r.commit_peak_mib = [long][Math]::Floor(($info.CommitPeak.ToUInt64() * $page) / 1MB)
        $r.commit_free_mib = $r.commit_limit_mib - $r.committed_mib
        $r.source = 'windows_performance_info'
    } catch {
        try {
            $perf = Get-CimInstance -ClassName Win32_PerfFormattedData_PerfOS_Memory -Property AvailableMBytes,CommittedBytes,CommitLimit -OperationTimeoutSec 3
            if ($null -ne $perf.AvailableMBytes -and $perf.CommitLimit -gt 0) {
                $r.available_mib = [long]$perf.AvailableMBytes
                $r.committed_mib = [long][Math]::Floor($perf.CommittedBytes / 1MB)
                $r.commit_limit_mib = [long][Math]::Floor($perf.CommitLimit / 1MB)
                $r.commit_free_mib = $r.commit_limit_mib - $r.committed_mib
                $r.source = 'windows_performance_counters'
            }
        } catch {}
    }
    return $r
}

function Get-Drives {
    $r = [ordered]@{}
    foreach ($entry in @(@('installation',$InstallRoot),@('temporary',[IO.Path]::GetTempPath()),@('downloads',$OutputDir))) {
        $d = $null
        try {
            if (Test-LocalPath $entry[1]) {
                $drive = [IO.DriveInfo]::new([IO.Path]::GetPathRoot($entry[1]))
                $d = [ordered]@{available_mib=[long][Math]::Floor($drive.AvailableFreeSpace / 1MB);
                    capacity_mib=[long][Math]::Floor($drive.TotalSize / 1MB)}
            }
        } catch {}
        $r[$entry[0]] = $d
    }
    return $r
}

function Get-Graphics {
    $r = [ordered]@{source='unavailable'; adapters=@(); dedicated_used_mib=$null; shared_used_mib=$null}
    try {
        $base = 'HKLM:\SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}'
        for ($i = 0; $i -lt 16; $i++) {
            try {
                $driver = Get-ItemProperty -LiteralPath (Join-Path $base $i.ToString('D4'))
                $vendor = 'other'
                if ($driver.ProviderName -match 'NVIDIA') { $vendor = 'nvidia' }
                elseif ($driver.ProviderName -match 'Advanced Micro Devices|AMD') { $vendor = 'amd' }
                elseif ($driver.ProviderName -match 'Intel') { $vendor = 'intel' }
                elseif ($driver.ProviderName -match 'Microsoft') { $vendor = 'microsoft' }
                $vram = $driver.'HardwareInformation.qwMemorySize'
                $mib = $null
                if ($vram -is [byte[]] -and $vram.Length -eq 8) { $vram = [BitConverter]::ToUInt64($vram,0) }
                if ($vram -is [long] -or $vram -is [uint64]) {
                    if ($vram -gt 0) { $mib = [long][Math]::Floor($vram / 1MB) }
                }
                $reported = $null
                $legacy = $driver.'HardwareInformation.MemorySize'
                if ($legacy -is [int] -and $legacy -ne 0) {
                    $reported = [long][Math]::Floor([BitConverter]::ToUInt32([BitConverter]::GetBytes($legacy),0) / 1MB)
                } elseif ($legacy -is [byte[]] -and $legacy.Length -eq 4) {
                    $reported = [long][Math]::Floor([BitConverter]::ToUInt32($legacy,0) / 1MB)
                }
                $version = Get-VersionValue $driver.DriverVersion -Package
                $device = $null
                if ($driver.MatchingDeviceId -match '^(?i:pci)\\ven_([0-9a-fA-F]{4})&dev_([0-9a-fA-F]{4})(?:&|$)') {
                    $device = ($Matches[1] + ':' + $Matches[2]).ToUpperInvariant()
                }
                $r.adapters += [ordered]@{vendor=$vendor; pci_device_type=$device; driver_version=$version; registry_vram_mib=$mib; legacy_reported_mib=$reported}
            } catch {}
        }
        if ($r.adapters.Count) { $r.source = 'windows_display_class_registry' }
    } catch {}
    try {
        $usage = @(Get-CimInstance -ClassName Win32_PerfFormattedData_GPUPerformanceCounters_GPUAdapterMemory -Property DedicatedUsage,SharedUsage -OperationTimeoutSec 3)
        if ($usage.Count) {
            $dedicated = 0.0
            $shared = 0.0
            foreach ($item in $usage) {
                if ($null -eq $item.DedicatedUsage -or $null -eq $item.SharedUsage) { throw 'unavailable' }
                $dedicated += [double]$item.DedicatedUsage
                $shared += [double]$item.SharedUsage
            }
            $r.dedicated_used_mib = [long][Math]::Floor($dedicated / 1MB)
            $r.shared_used_mib = [long][Math]::Floor($shared / 1MB)
        }
    } catch {}
    return $r
}

function Get-PageFiles {
    $r = [ordered]@{source='unavailable'; files=$null; allocated_mib=$null; used_mib=$null; peak_used_mib=$null; configuration=$null}
    try {
        $cfg = (Get-ItemProperty -LiteralPath 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management' -Name PagingFiles).PagingFiles
        $r.configuration = 'configured'
        if (!$cfg) { $r.configuration = 'none_listed' }
        elseif (@($cfg | Where-Object { $_ -match '\s0\s+0$|^\?:' }).Count) { $r.configuration = 'system_managed_entry' }
    } catch {}
    try {
        $files = @(Get-CimInstance -ClassName Win32_PageFileUsage -Property AllocatedBaseSize,CurrentUsage,PeakUsage -OperationTimeoutSec 3)
        $r.source = 'windows_pagefile_usage'
        $r.files = $files.Count
        $r.allocated_mib = 0L
        $r.used_mib = 0L
        $r.peak_used_mib = 0L
        foreach ($item in $files) {
            $r.allocated_mib += [long]$item.AllocatedBaseSize
            $r.used_mib += [long]$item.CurrentUsage
            $r.peak_used_mib += [long]$item.PeakUsage
        }
    } catch {}
    return $r
}

function Get-Workers {
    $r = [ordered]@{matched=0; inaccessible=0; private_mib=0L; working_set_mib=0L}
    $prefix = $InstallRoot.TrimEnd('\') + '\'
    foreach ($name in 'python','pythonw','TotalSegmentator','nnUNetv2_predict') {
        foreach ($process in @([Diagnostics.Process]::GetProcessesByName($name))) {
            try {
                if ($process.MainModule.FileName.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
                    $r.matched++
                    $r.private_mib += [long][Math]::Floor($process.PrivateMemorySize64 / 1MB)
                    $r.working_set_mib += [long][Math]::Floor($process.WorkingSet64 / 1MB)
                }
            } catch { $r.inaccessible++ } finally { $process.Dispose() }
        }
    }
    return $r
}

function Get-ExhaustionEvents {
    $r = [ordered]@{window_hours=24; matches=$null; capped=$false}
    try {
        $filter = @{LogName='System'; ProviderName='Microsoft-Windows-Resource-Exhaustion-Detector'; Id=2004; StartTime=[datetime]::Now.AddDays(-1)}
        $events = @(Get-WinEvent -FilterHashtable $filter -MaxEvents 32)
        $r.matches = $events.Count
        $r.capped = $events.Count -eq 32
    } catch {
        if ($_.FullyQualifiedErrorId -like 'NoMatchingEventsFound,*') { $r.matches = 0 }
    }
    return $r
}

function Get-Plugin([string]$Name) {
    $base = Join-Path $InstallRoot ('Plugins\' + $Name)
    $file = Join-Path $base 'installation.json'
    $s = Read-Object $file
    $state = 'absent'
    if ($s) {
        $state = 'unrecognized'
        foreach ($choice in 'ready','active','installed','prepared','pending','installing','failed','inactive','committed') {
            if ($s.state -ceq $choice) { $state = $choice; break }
        }
    } elseif (Test-PlainPath $file) { $state = 'unreadable' }
    $code = Get-VersionValue $s.active_version
    $bundle = Get-VersionValue $s.resource_bundle_version
    $r = [ordered]@{receipt_state=$state; active_code_version=$code; active_code_directory_exists=$false;
        weight_bundle_version=$bundle; resource_receipt_declared=$false; maintenance_state=$null; maintenance_code=$null}
    if ($code) {
        $r.active_code_directory_exists = Test-PlainPath (Join-Path $base ('versions\' + $code))
    }
    $r.resource_receipt_declared = [bool]($s.resources -or ($s.reports_installed -is [bool] -and $s.reports_installed))
    $status = Read-Object (Join-Path $base 'external-status.json')
    foreach ($choice in 'pending','running','ready','completed','failed','error','interrupted','staging','cancelled','waiting') {
        if ($status.state -ceq $choice) { $r.maintenance_state = $choice }
    }
    foreach ($code in 'DOWNLOAD_FAILED','INSTALL_FAILED','BUNDLE_INCOMPLETE','LOCAL_RESOURCES_MISSING','WRONG_PLUGIN','BASE_UNSUPPORTED','INTEGRITY_FAILED','NO_SPACE','DISK_FULL') {
        if ($status.code -ceq $code -or $status.error.code -ceq $code) { $r.maintenance_code = $code }
    }
    return $r
}

function Get-Packages {
    $site = Join-Path $InstallRoot 'python\Lib\site-packages'
    $packages = [ordered]@{}
    $modules = [ordered]@{numpy='numpy'; scipy='scipy'; pydicom='pydicom'; nibabel='nibabel';
        torch='torch'; totalsegmentator='totalsegmentator'; nnunetv2='nnunetv2'; simpleitk='SimpleITK';
        rt_utils='rt_utils'; opencv_python='cv2'; scikit_image='skimage'; monai='monai'}
    foreach ($name in $modules.Keys) {
        $packages[$name] = [ordered]@{module_present=(Test-PlainPath (Join-Path $site $modules[$name])); metadata_version=$null}
    }
    try {
        if (Test-PlainPath $site) {
            foreach ($dir in [IO.Directory]::EnumerateDirectories($site,'*.dist-info')) {
                $leaf = [IO.Path]::GetFileName($dir)
                if ($leaf -match '^([a-z0-9_]+)-([^\s]+)\.dist-info$' -and $packages.Contains($Matches[1])) {
                    $key = $Matches[1]
                    $ver = $Matches[2]
                    $packages[$key].metadata_version = Get-VersionValue $ver -Package
                }
                if ($clock.Elapsed.TotalSeconds -gt 35) { break }
            }
        }
    } catch {}
    return $packages
}

function Get-EngineHistory {
    $s = Read-Object (Join-Path $InstallRoot 'calibracao\memoria-motor-v1.json')
    if (!(($s.schema -is [long] -or $s.schema -is [int]) -and $s.schema -eq 1)) { return $null }
    $r = [ordered]@{}
    foreach ($phase in 'inference','postprocess','write_full','write_study','write_other','pipeline') {
        $p = $s.phases.$phase
        if ($null -eq $p) { continue }
        $v = [ordered]@{}
        foreach ($k in 'samples','available_min_mib','commit_free_min_mib','private_max_mib','working_set_max_mib','physical_total_mib','commit_limit_mib') {
            $v[$k] = Get-CountValue $p.$k
        }
        $r[$phase] = $v
    }
    return $r
}

function Add-Signals($Summary, [string]$Body, [string]$Source) {
    if (!$Body) { return }
    $memoryError = '(?<![a-z])(?:_Array)?MemoryError\b|Unable to allocate|not enough memory|std::bad_alloc'
    $gpuError = 'CUDA(?: error:)? out of memory|torch\.cuda\.OutOfMemoryError'
    $patterns = [ordered]@{allocation=$memoryError;
        gpu_memory=$gpuError; disk_full='WinError 112|ENOSPC|No space left on device';
        access_denied='PermissionError|WinError 5\b'; invalid_dicom='InvalidDicomError';
        missing_referenced_image='not present for creating 3D Image'; invalid_decimal='Invalid value for VR DS|exceeds the maximum length of 16 allowed for VR DS';
        upload_size='HTTP\s*413|413 Request Entity Too Large'; download_failed='\bDOWNLOAD_FAILED\b';
        install_failed='\bINSTALL_FAILED\b'; delivery_failed='O CONJUNTO ENTREGUE NAO SAIU'}
    foreach ($key in $patterns.Keys) {
        $hits = [regex]::Matches($Body, $patterns[$key], 'IgnoreCase')
        $Summary.matches[$key] += $hits.Count
    }
    $families = [ordered]@{aorta_great_arteries='aorta|great[_ ]?arteries|compostos de vaso'; skin='\bskin(?:_|\b)|\bpele\b';
        chest_wall_ribs='chestwall|chest_wall|costel|esqueleto_toracico'; bowel='bag_bowel|\bbowel\b';
        cardiac='\bheart(?:_|\b)|pericard'; iliac='iliac_crest'; lung='\blungs?(?:_|\b)|pulm[oa]'; cervical='parotid|mandib|\blnl';}
    $stages = [ordered]@{smoothing='suaviza|smooth'; construction='segunda passada'; cropping='recorte|clip';
        finishing='acabamento'; single_contour='um contorno por corte'; delivery='CONJUNTO ENTREGUE NAO SAIU'}
    $inTrace = $false
    $traceStage = $null
    $traceFamily = $null
    foreach ($rawLine in ($Body -split '\r?\n')) {
        $line = $rawLine -replace '^\[\d\d/\d\d \d\d:\d\d:\d\d\] ', ''
        if ($line -match '^\s*Traceback \(most recent call last\):\s*$') {
            $inTrace = $true
            $traceStage = $null
            $traceFamily = $null
            $frame = ''
            continue
        }
        if ($inTrace -and $line -match '^\s+File "(?:<caminho>|(?:[^"]*[\\/])?engine\.py)", line \d+, in ([A-Za-z0-9_]+)\s*$') {
            $function = $Matches[1]
            $frame = $function
            if ($function -in '_suavizar_individuais','_suavizar_construcoes','suavizar_em_grupos','_suavizar_contornos') { $traceStage = 'smoothing' }
            if ($function -in 'acabamentos_terminais','_trocar_mascara_terminal') { $traceStage = 'finishing' }
            if ($function -eq 'recortar_aorta_dos_vizinhos') { $traceStage = 'cropping'; $traceFamily = 'aorta_great_arteries' }
            if ($function -in '_construir_bag_bowel','_construir_bag_bowel_oar') { $traceFamily = 'bowel' }
            if ($function -in '_construir_coracao','_construir_pericardio') { $traceFamily = 'cardiac' }
            if ($function -eq '_construir_cristas_iliacas') { $traceFamily = 'iliac' }
            if ($function -eq '_construir_pulmoes') { $traceFamily = 'lung' }
            continue
        }
        if ($inTrace -and $line -match '^\s+File "' ) { $frame = ''; continue }
        if ($inTrace -and $frame -eq 'acabamentos_terminais' -and $line.Trim() -ceq 'masks[aorta] = ao & ~es') {
            $traceFamily = 'aorta_great_arteries'
            continue
        }
        # Python frames/source lines are indented; an unindented line ends this traceback.
        $exception = $line -match '^\s*(?:[A-Za-z_]\w*\.)*(?:[A-Za-z_]\w*(?:Error|Exception)|Exception|KeyboardInterrupt|SystemExit)(?::|\s*$)'
        if ($inTrace -and $line -match '^\s' -and !$exception) { continue }
        $wasTrace = $inTrace -and $exception
        $inTrace = $false
        if ($line -notmatch "$memoryError|$gpuError") { continue }
        $Summary.oom_lines_by_source[$Source]++
        $familyFound = $false
        $stageFound = $false
        foreach ($key in $families.Keys) {
            if ($line -match $families[$key]) { $Summary.oom_lines_by_family[$key]++; $familyFound = $true }
        }
        foreach ($key in $stages.Keys) {
            if ($line -match $stages[$key]) { $Summary.oom_lines_by_stage[$key]++; $stageFound = $true }
        }
        if (!$familyFound -and $wasTrace -and $traceFamily) {
            $Summary.oom_lines_by_family[$traceFamily]++; $familyFound = $true
        }
        if (!$stageFound -and $wasTrace -and $traceStage) {
            $Summary.oom_lines_by_stage[$traceStage]++; $stageFound = $true
        }
        if (!$familyFound) { $Summary.oom_family_unknown++ }
        if (!$stageFound) { $Summary.oom_stage_unknown++ }
    }
    foreach ($m in [regex]::Matches($Body, '(?i)Unable to allocate\s+(\d{1,8}(?:\.\d{0,3})?)\s+(KiB|MiB|GiB)')) {
        $v = [double]::Parse($m.Groups[1].Value, [Globalization.CultureInfo]::InvariantCulture)
        if ($m.Groups[2].Value -ieq 'GiB') { $v *= 1024 }
        if ($m.Groups[2].Value -ieq 'KiB') { $v /= 1024 }
        $v = [long][Math]::Ceiling($v)
        if ($Summary.max_refused_allocation_mib -lt $v) { $Summary.max_refused_allocation_mib = $v }
    }
}

function Get-Incidents {
    $r = [ordered]@{sources_read=0; records_sampled=0; recorded_success=0; recorded_failure=0; case_logs_read=0;
        oom_lines_by_source=[ordered]@{station_log=0;case_log=0;case_result=0;index_error=0}; oom_family_unknown=0; oom_stage_unknown=0;
        sampled_local_day=[ordered]@{day=$now.ToLocalTime().ToString('yyyy-MM-dd'); dated_attempts=0;
            success=0;failure=0;ct_success=0;ct_failure=0;unknown_modality=0;undated_index_rows=0;
            bounded=$false;index_available=$false};
        max_refused_allocation_mib=$null; oom_lines_by_family=[ordered]@{aorta_great_arteries=0;skin=0;chest_wall_ribs=0;bowel=0;cardiac=0;iliac=0;lung=0;cervical=0};
        oom_lines_by_stage=[ordered]@{smoothing=0;construction=0;cropping=0;finishing=0;single_contour=0;delivery=0};
        matches=[ordered]@{allocation=0;gpu_memory=0;disk_full=0;access_denied=0;
        invalid_dicom=0;missing_referenced_image=0;invalid_decimal=0;upload_size=0;download_failed=0;install_failed=0;delivery_failed=0}}
    foreach ($leaf in 'INSTALL_LOG.txt','radai_atualizar.log','radai_lancador.log','preparar_log.txt','radai_vigia.log','calibracao\radai_vigia.log','_instalacao\configurar_ambiente_log.txt') {
        $text = Read-BoundedText (Join-Path $InstallRoot $leaf) 262144 -Tail
        if ($null -ne $text) { $r.sources_read++; Add-Signals $r $text 'station_log' }
    }
    $indexPath = Join-Path $InstallRoot 'registro\indice.jsonl'
    $index = Read-BoundedText $indexPath 1048576 -Tail
    $day = $r.sampled_local_day
    $day.index_available = $null -ne $index
    if ($day.index_available) {
        try { $day.bounded = [IO.FileInfo]::new($indexPath).Length -gt 1048576 } catch { $day.bounded = $true }
    }
    if (!$index) { return $r }
    $lines = @($index.TrimEnd([char]13,[char]10) -split '\r?\n')
    if ($lines.Count -gt 512) { $lines = $lines[-512..-1]; $day.bounded = $true }
    [array]::Reverse($lines)
    $cases = @{}
    $orderedRows = [Collections.Generic.List[object]]::new()
    foreach ($line in $lines) {
        if ($clock.Elapsed.TotalSeconds -ge 38) { $day.bounded = $true; break }
        if ($line.Length -gt 8192) { $day.bounded = $true; continue }
        try { $row = ConvertFrom-Json -InputObject $line } catch { $day.bounded = $true; continue }
        if ($row.ok -isnot [bool]) { $day.bounded = $true; continue }
        $case = $row.pasta
        $valid = $case -is [string] -and $case -cmatch '\A\d{4}-\d\d-\d\d_\d{6}_(?:[a-f0-9]{8}|semuid00)(?:_\d{1,3})?\z'
        if ($valid) {
            if ($cases.ContainsKey($case)) { continue }
            $cases[$case] = $true
        }
        $r.records_sampled++
        if ($row.ok) { $r.recorded_success++ } else { $r.recorded_failure++ }
        $today = $false
        $stamp = [DateTimeOffset]::MinValue
        if ($row.quando -is [string] -and [DateTimeOffset]::TryParseExact($row.quando, 'yyyy-MM-ddTHH:mm:sszzz',
            [Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::None,[ref]$stamp)) {
            $today = $stamp.LocalDateTime.ToString('yyyy-MM-dd') -eq $day.day
        } else { $day.undated_index_rows++ }
        if ($today) {
            $day.dated_attempts++
            if ($row.ok) { $day.success++ } else { $day.failure++ }
            $day.unknown_modality++
        }
        $orderedRows.Add([pscustomobject]@{index=$row;valid=$valid;today=$today})
    }
    # Read failures first. A series that completed after a failure must not consume its log slot.
    $detailsRead = 0
    foreach ($entry in @($orderedRows | Where-Object { !$_.index.ok }) + @($orderedRows | Where-Object { $_.index.ok })) {
        $row = $entry.index
        if (!$entry.valid -or $clock.Elapsed.TotalSeconds -ge 38) {
            Add-Signals $r ([string]$row.erro) 'index_error'
            continue
        }
        $folder = Join-Path $InstallRoot ('registro\casos\' + $row.pasta)
        $details = $null
        if ((!$row.ok -or $entry.today) -and $detailsRead -lt 128) {
            $detailsRead++
            try {
                $raw = Read-BoundedText (Join-Path $folder 'caso.json') 1048576
                if ($raw) { $details = ConvertFrom-Json -InputObject $raw }
            } catch {}
        }
        if ($entry.today -and $details.serie.modalidade_origem -eq 'dicom' -and $details.serie.modalidade -match '^[a-z]{2,4}$') {
            $day.unknown_modality--
            if ($details.serie.modalidade -eq 'CT') {
                if ($row.ok) { $day.ct_success++ } else { $day.ct_failure++ }
            }
        }
        $caseLog = $null
        if ($r.case_logs_read -lt 12) {
            $caseLog = Read-BoundedText (Join-Path $folder 'log.txt') 262144 -Tail
        }
        if ($null -ne $caseLog) { $r.case_logs_read++; Add-Signals $r $caseLog 'case_log' }
        $detailError = [string]$details.resultado.erro
        $indexError = [string]$row.erro
        if ($detailError -and (!$caseLog -or !$caseLog.Contains($detailError))) {
            Add-Signals $r $detailError 'case_result'
        } elseif (!$detailError -and $indexError -and (!$caseLog -or !$caseLog.Contains($indexError))) {
            Add-Signals $r $indexError 'index_error'
        }
    }
    return $r
}

try {
    if (!$InstallRoot -and !$Quiet) {
        Add-Type -AssemblyName System.Windows.Forms
        $folder = New-Object Windows.Forms.FolderBrowserDialog
        try {
            $folder.Description = 'Escolha a pasta de instalação da Local Suite (onde está entrega.txt).'
            $folder.ShowNewFolderButton = $false
            if ($folder.ShowDialog() -ne [Windows.Forms.DialogResult]::OK) { exit 4 }
            $InstallRoot = $folder.SelectedPath
        } finally { $folder.Dispose() }
    }
    if (!$InstallRoot -or !(Test-PlainPath $InstallRoot)) { throw 'root' }
    $InstallRoot = [IO.Path]::GetFullPath($InstallRoot)
    $release = Read-BoundedText (Join-Path $InstallRoot 'entrega.txt') 32768
    if ($release -notmatch '(?m)^PROJETO=LOCAL_SUITE\r?$') { throw 'root' }
} catch {
    Show-Message 'Escolha a pasta de instalação da Local Suite que contém entrega.txt.'
    exit 2
}

$partial = $null
$ownsStaging = $false
try {
    if (!$OutputDir) {
        $prop = '{374DE290-123F-4565-9164-39C4925E467B}'
        try {
            $custom = (Get-ItemProperty -LiteralPath 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders').$prop
            if ($custom) { $OutputDir = [Environment]::ExpandEnvironmentVariables($custom) }
        } catch {}
        if (!$OutputDir) { $OutputDir = Join-Path ([Environment]::GetFolderPath('UserProfile')) 'Downloads' }
    }
    $OutputDir = [IO.Path]::GetFullPath($OutputDir)
    # GUARDA: o Windows pode redirecionar Downloads. O destino recebe apenas o ZIP de nome único.
    [void][IO.Directory]::CreateDirectory($OutputDir)
    $version = $null
    $minimum = $null
    if ($release -match '(?m)^VERSAO=([^\r\n]+)\r?$') { $version = Get-VersionValue $Matches[1] }
    if ($release -match '(?m)^BUNDLE_MINIMO=([^\r\n]+)\r?$') { $minimum = Get-VersionValue $Matches[1] }
    $python = Join-Path $InstallRoot 'python\python.exe'
    $pythonVersion = $null
    if (Test-PlainPath $python) {
        try { $pythonVersion = Get-VersionValue ([Diagnostics.FileVersionInfo]::GetVersionInfo($python).ProductVersion) } catch {}
    }
    $files = [ordered]@{}
    foreach ($leaf in 'engine.py','radai_web.py','radai_dicom.py','radai_plugin_seeds.py','radai_plugins.py','radai_records.py','radai_neuro_install.py','radai_lung_install.py','_requisitos.json') {
        $files[$leaf] = Test-PlainPath (Join-Path $InstallRoot $leaf)
    }
    $catalog = $null
    $weights = Join-Path $InstallRoot 'ts_weights'
    if (Test-PlainPath $weights) {
        try { $catalog = @([IO.Directory]::EnumerateDirectories($weights,'Dataset*') | Select-Object -First 513).Count } catch {}
    }
    $now = [datetime]::UtcNow
    $report = [ordered]@{
        schema='local-suite.station-diagnostics/1'; captured_utc=$now.ToString('yyyy-MM-ddTHH:mm:ssZ');
        os=[ordered]@{windows_build=[Environment]::OSVersion.Version.Build; os_64bit=[Environment]::Is64BitOperatingSystem;
            collector_64bit=[Environment]::Is64BitProcess; logical_processors=[Environment]::ProcessorCount;
            powershell_major=$PSVersionTable.PSVersion.Major; powershell_minor=$PSVersionTable.PSVersion.Minor};
        memory=(Get-MemorySnapshot); pagefile=(Get-PageFiles); resource_exhaustion_events=(Get-ExhaustionEvents);
        disk=(Get-Drives); graphics=(Get-Graphics); suite_processes=(Get-Workers);
        installation=[ordered]@{suite_version=$version; minimum_bundle=$minimum; python_binary_version=$pythonVersion;
            files=$files; ts_dataset_directory_count=$catalog; packages=(Get-Packages);
            neuro=(Get-Plugin 'NEURO RT'); lung=(Get-Plugin 'LUNG RT')};
        incident_signals=(Get-Incidents); engine_phase_history=(Get-EngineHistory)
    }
    $json = ConvertTo-Json -InputObject $report -Depth 8
    $leaf = 'LocalSuite-Diagnostico-' + $now.ToString('yyyyMMddTHHmmssZ') + '-' + [guid]::NewGuid().ToString('N').Substring(0,8) + '.zip'
    $target = Join-Path $OutputDir $leaf
    $partial = $target + '.part'
    Add-Type -AssemblyName System.IO.Compression
    $stream = [IO.File]::Open($partial, 'CreateNew', 'Write', 'None')
    $ownsStaging = $true
    try {
        $zip = [IO.Compression.ZipArchive]::new($stream, 'Create', $true)
        try {
            $member = $zip.CreateEntry('diagnostico.json')
            $write = $member.Open()
            try { $bytes = $utf8.GetBytes($json); $write.Write($bytes, 0, $bytes.Length) } finally { $write.Dispose() }
        } finally { $zip.Dispose() }
        $stream.Flush($true)
    } finally { $stream.Dispose() }
    [IO.File]::Move($partial, $target)
    $ownsStaging = $false
} catch {
    Show-Message 'Não foi possível gravar o diagnóstico. Confira o espaço e o acesso à pasta Downloads.'
    exit 3
} finally {
    if ($ownsStaging -and $partial) { try { [IO.File]::Delete($partial) } catch {} }
}
if ($Quiet) { [Console]::Out.WriteLine($leaf) }
else { Show-Message ('Diagnóstico salvo em Downloads.' + [Environment]::NewLine + $leaf) }
exit 0
