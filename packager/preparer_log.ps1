[CmdletBinding()]
param(
    [ValidateSet('Podar', 'Cauda')][string]$Modo = 'Cauda',
    [int]$Linhas = 15,
    [int]$Manter = 20
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$log = [string]$env:RADAI_LOG_PREPARADOR
if (-not $log) { exit 0 }

if ($Modo -eq 'Podar') {
    try {
        $pasta = Split-Path -Parent $log
        Get-ChildItem -LiteralPath $pasta -Filter 'preparer_*.log' -File |
            Sort-Object -Property LastWriteTime -Descending |
            Select-Object -Skip $Manter |
            ForEach-Object {
                try { Remove-Item -LiteralPath $_.FullName -Force } catch { }
            }
    } catch { }
    exit 0
}

function PaginaDoConsole {
    $cp = 0
    try { $cp = [Console]::OutputEncoding.CodePage } catch { $cp = 0 }
    if ($cp -le 0 -or $cp -eq 65001) {
        try {
            $cp = [int](Get-ItemProperty -LiteralPath 'HKLM:\SYSTEM\CurrentControlSet\Control\Nls\CodePage' -Name OEMCP).OEMCP
        } catch { $cp = 437 }
    }
    return [System.Text.Encoding]::GetEncoding($cp)
}

try {
    $bytes = [System.IO.File]::ReadAllBytes($log)
} catch {
    Write-Output ('   (could not read the log: ' + $_.Exception.Message + ')')
    exit 0
}
$utf8 = New-Object System.Text.UTF8Encoding($false, $true)
$oem = PaginaDoConsole

$fimUtil = $bytes.Length
if ($fimUtil -gt 0 -and $bytes[$fimUtil - 1] -eq 10) { $fimUtil-- }
$ini = 0
$k = $fimUtil - 1
for ($c = 0; $c -lt $Linhas -and $k -ge 0; $c++) {
    $nl = [Array]::LastIndexOf($bytes, [byte]10, $k)
    if ($nl -lt 0) { $ini = 0; break }
    $ini = $nl + 1
    $k = $nl - 1
}
$partes = New-Object System.Collections.ArrayList
$a0 = $ini
for ($i = $ini; $i -lt $fimUtil; $i++) {
    if ($bytes[$i] -eq 10) {
        [void]$partes.Add(@($a0, $i))
        $a0 = $i + 1
    }
}
if ($a0 -le $fimUtil -and $fimUtil -gt $ini) { [void]$partes.Add(@($a0, $fimUtil)) }
for ($j = 0; $j -lt $partes.Count; $j++) {
    $a = $partes[$j][0]; $b = $partes[$j][1]
    if ($b -gt $a -and $bytes[$b - 1] -eq 13) { $b-- }
    $n = $b - $a
    $s = ''
    if ($n -gt 0) {
        try { $s = $utf8.GetString($bytes, $a, $n) }
        catch { $s = $oem.GetString($bytes, $a, $n) }
        $s = $s.TrimStart([char]0xFEFF)
    }
    Write-Output ('   ' + $s)
}

if ([string]$env:RADAI_RC -eq '-805306369') {
    Write-Output ''
    Write-Output '   Error -805306369 usually means the preparer did not finish by itself:'
    Write-Output '   it was closed from outside - for example, a window that Windows'
    Write-Output '   marked Not Responding and that was then closed. The last lines'
    Write-Output '   above show the step it was in. Run it again.'
}
exit 0
