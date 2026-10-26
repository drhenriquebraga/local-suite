param([switch]$SemPerguntar, [string]$Alvo = "",
      [switch]$Guardar,
      [switch]$ApagarFora,
      [int]$EsperarFechar = 0)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$AQUI = $PSScriptRoot
if (-not $AQUI) { $AQUI = Split-Path -Parent $MyInvocation.MyCommand.Path }
if ($Alvo) {
    $AQUI = $Alvo
} else {
    $tenta = $AQUI
    for ($i = 0; $i -lt 4; $i++) {
        if (-not $tenta) { break }
        $tem = $true
        foreach ($m in @("radai_watcher.py", "entrega.txt")) {
            if (-not (Test-Path -LiteralPath (Join-Path $tenta $m))) { $tem = $false }
        }
        if ($tem) { $AQUI = $tenta; break }
        $acima = Split-Path -Parent $tenta
        if (-not $acima -or $acima -eq $tenta) { break }
        $tenta = $acima
    }
}
$LOG = Join-Path $env:TEMP ("radai_desinstalar_" + (Get-Random) + ".txt")

function Diga($t)  { Write-Host $t }
function Anote($t) { try { Add-Content -LiteralPath $LOG -Value $t -Encoding UTF8 } catch { } }
function Pare($t) {
    Diga ""
    Diga "============================================================"
    Diga "  NOTHING WAS DELETED"
    Diga ""
    foreach ($l in ($t -split "`n")) { Diga ("  " + $l) }
    Diga "============================================================"
    Diga ""
    Anote ("PAROU: " + $t)
    exit 1
}

Diga "============================================================"
Diga "  Radioterapia.ai Local Suite - uninstall"
Diga "============================================================"
Diga ""
Diga ("  Pasta: " + $AQUI)
Anote ("alvo=" + $AQUI)

$MARCAS = @("radai_watcher.py", "entrega.txt")
$faltam = @()
foreach ($m in $MARCAS) {
    if (-not (Test-Path -LiteralPath (Join-Path $AQUI $m))) { $faltam += $m }
}
if ($faltam.Count -gt 0) {
    Pare ("Esta pasta nao parece uma instalacao do programa, e nao achei" +
          [char]10 +
          "nenhuma subindo a partir dela." + [char]10 +
          "Faltam as marcas: " + ($faltam -join ", ") + [char]10 + [char]10 +
          "Se o programa estiver instalado em outro lugar, aponte:" +
          [char]10 +
          '  UNINSTALL.ps1 -Alvo "<a pasta que tem o radai_watcher.py>"')
}
$raizCurta = [System.IO.Path]::GetPathRoot($AQUI)
if ($AQUI.TrimEnd("\") -eq $raizCurta.TrimEnd("\")) {
    Pare "O alvo e a raiz de um disco. Recusado."
}

$porta = 8777
try {
    $cfg = Join-Path $AQUI "radai_watcher.config"
    if (Test-Path -LiteralPath $cfg) {
        foreach ($l in (Get-Content -LiteralPath $cfg -Encoding UTF8)) {
            if ($l -match "^\s*PORT\s*=\s*(\d+)") { $porta = [int]$Matches[1] }
        }
    }
} catch { }
function _PortaViva($p) {
    try {
        $c = New-Object System.Net.Sockets.TcpClient
        $c.Connect("127.0.0.1", $p)
        $v = $c.Connected
        $c.Close()
        return $v
    } catch { return $false }
}
$emUso = _PortaViva $porta
if ($emUso -and $EsperarFechar -gt 0) {
    Diga ("  esperando o programa fechar (ate " + $EsperarFechar + "s)...")
    for ($i = 0; $i -lt $EsperarFechar; $i++) {
        Start-Sleep -Seconds 1
        if (-not (_PortaViva $porta)) { $emUso = $false; break }
    }
}
function _EONossoPainel($p) {
    try {
        $req = [System.Net.WebRequest]::Create("http://127.0.0.1:" + $p + "/api/pulso")
        # GUARDA: sem Proxy nulo o pedido ao 127.0.0.1 vai ao proxy do Windows.
        $req.Proxy = $null
        $req.Timeout = 3000
        $resp = $req.GetResponse()
        try {
            $sr = New-Object System.IO.StreamReader($resp.GetResponseStream())
            $txt = $sr.ReadToEnd()
            $sr.Close()
        } finally { $resp.Close() }
        return ($txt -match '"radai"\s*:\s*true')
    } catch { return $false }
}
if ($emUso -and (_EONossoPainel $porta)) {
    Pare ("O Radioterapia.AI Local Suite esta RODANDO na porta " + $porta + "." + [char]10 + [char]10 +
          "Ele roda sem janela: abra o painel (http://127.0.0.1:" + $porta + "/)," + [char]10 +
          "clique em FECHAR APP > Fechar tudo e rode este arquivo de novo." + [char]10 + [char]10 +
          "Apagar por baixo de um vigia em execucao deixa o processo vivo" + [char]10 +
          "com os arquivos sumindo -- e o log da noite vira ficcao.")
}
if ($emUso) {
    Pare ("Alguem esta atendendo na porta " + $porta + " (a deste programa)" + [char]10 +
          "e nao responde como o painel do Local Suite." + [char]10 + [char]10 +
          "Se o Local Suite estiver travado, feche o python.exe dele no" + [char]10 +
          "Gerenciador de Tarefas. Se for outro programa, feche-o, e rode" + [char]10 +
          "este arquivo de novo." + [char]10 + [char]10 +
          "Apagar por baixo de um vigia em execucao deixa o processo vivo" + [char]10 +
          "com os arquivos sumindo -- e o log da noite vira ficcao.")
}

$bytes = 0
$narq = 0
try {
    $m = Get-ChildItem -LiteralPath $AQUI -Recurse -File -ErrorAction SilentlyContinue |
         Measure-Object -Property Length -Sum
    $bytes = [int64]$m.Sum
    $narq = $m.Count
} catch { }
Diga ("  " + $narq + " arquivos, " + ("{0:N2}" -f ($bytes / 1GB)) + " GB")

$PRESERVAVEL = @("radai_watcher.config", "_dados.txt", "_bundle.txt",
                 "calibracao", "registro", "radai_status.json",
                 "nomes_proprios.json", "protocolos_proprios.json")
$achados = @()
foreach ($n in $PRESERVAVEL) {
    if (Test-Path -LiteralPath (Join-Path $AQUI $n)) { $achados += $n }
}
foreach ($f in (Get-ChildItem -LiteralPath $AQUI -Filter "*.log" -File -ErrorAction SilentlyContinue)) {
    $achados += $f.Name
}

Diga ""
Diga "  WILL BE DELETED"
Diga ("    a pasta inteira: " + $AQUI)
Diga "    the desktop shortcut and the Start menu one"
Diga "    this program entry in _instalados.json"
Diga ""
if ($achados.Count -gt 0) {
    Diga "  WHAT YOU BUILT, and a reinstall will not bring back:"
    foreach ($a in $achados) { Diga ("    " + $a) }
} else {
    Diga "  There is no local data of yours in this folder."
}
Diga ""


function Perguntar($rotulo, $padrao) {
    $v = $null
    try { $v = Read-Host $rotulo } catch { $v = $null }
    if ($null -eq $v) { return $padrao }
    return [string]$v
}

function _UnidadesLocais {
    # GUARDA: a bateria aponta as unidades para uma pasta propria; sem isso
    # ela listaria (e poderia apagar) o temporario de quem a roda.
    if ($env:RADAI_UNIDADES_LOCAIS) {
        return @($env:RADAI_UNIDADES_LOCAIS -split ";" | Where-Object { $_ })
    }
    $r = @()
    try {
        foreach ($d in [System.IO.DriveInfo]::GetDrives()) {
            if ($d.DriveType -eq "Fixed" -and $d.IsReady) { $r += $d.RootDirectory.FullName }
        }
    } catch { }
    return $r
}
function _DentroDaPasta($c) {
    $a = [System.IO.Path]::GetFullPath($AQUI).TrimEnd("\") + "\"
    $b = [System.IO.Path]::GetFullPath($c).TrimEnd("\") + "\"
    return $b.StartsWith($a, [System.StringComparison]::OrdinalIgnoreCase)
}
$FORA = @()
$tmps = @()
foreach ($u in (_UnidadesLocais)) { $tmps += (Join-Path (Join-Path $u "RADIOTERAPIA_AI") "tmp") }
if ($env:TEMP) { $tmps += $env:TEMP }
foreach ($t in ($tmps | Select-Object -Unique)) {
    if (-not (Test-Path -LiteralPath $t)) { continue }
    foreach ($i in (Get-ChildItem -LiteralPath $t -Filter "radai_*" -Force -ErrorAction SilentlyContinue)) {
        if ($i.Name -like "radai_desinstalar_*" -or $i.Name -like "radai_rm_*") { continue }
        if (_DentroDaPasta $i.FullName) { continue }
        $FORA += $i.FullName
    }
}
if ($env:LOCALAPPDATA) {
    $la = Join-Path $env:LOCALAPPDATA "RADIOTERAPIA_AI"
    if (Test-Path -LiteralPath $la) {
        foreach ($i in (Get-ChildItem -LiteralPath $la -Filter "motor_*.json" -File -ErrorAction SilentlyContinue)) {
            $FORA += $i.FullName
        }
    }
}
$dadosEm = ""
foreach ($p in @($AQUI, (Split-Path -Parent $AQUI))) {
    if ($dadosEm -or -not $p) { continue }
    $arq = Join-Path $p "_dados.txt"
    if (-not (Test-Path -LiteralPath $arq)) { continue }
    try {
        foreach ($l in (Get-Content -LiteralPath $arq -Encoding UTF8)) {
            $l = $l.Trim().Trim('"')
            if ($l -and -not $l.StartsWith("#")) { $dadosEm = $l; break }
        }
    } catch { }
}
if ($dadosEm) {
    try {
        $cache = Join-Path (Split-Path -Parent ([System.IO.Path]::GetFullPath($dadosEm).TrimEnd("\"))) "cache_tasks"
        if ((Test-Path -LiteralPath $cache) -and -not (_DentroDaPasta $cache)) { $FORA += $cache }
    } catch { }
}
$apagarFora = $false
if ($FORA.Count -gt 0) {
    Diga "  OUTSIDE THIS FOLDER (temporary series copies, the task cache,"
    Diga "  the engine console and the browser profile of the panel):"
    foreach ($f in $FORA) { Diga ("    " + $f) }
    Anote ("fora da pasta: " + $FORA.Count + " item(ns)")
    if ($ApagarFora) {
        $apagarFora = $true
        Diga "  outside items: WILL BE DELETED (asked by the caller)"
    } elseif ($SemPerguntar) {
        Diga "  outside items: KEPT (pass -ApagarFora to delete them)"
    } else {
        Diga "  Delete these too? Type YES to delete them. ENTER keeps them."
        $rf = Perguntar "  [ENTER = keep]" ""
        $xf = $rf.Trim().ToUpperInvariant()
        $apagarFora = ($xf -eq "YES" -or $xf -eq "SIM")
    }
    Diga ""
}

$guardarEm = ""
if ($achados.Count -gt 0 -and $Guardar) {
    $carimbo = (Get-Date -Format "yyyy-MM-dd_HHmm")
    $guardarEm = Join-Path (Split-Path -Parent $AQUI) `
                 ((Split-Path -Leaf $AQUI) + "_GUARDADO_" + $carimbo)
    Diga ("  guardar: SIM (pedido por quem chamou) -> " + $guardarEm)
} elseif ($achados.Count -gt 0 -and $SemPerguntar) {
    Diga ("  guardar: NAO (pedido por quem chamou) — " +
          $achados.Count + " item(ns) vao junto com a pasta")
} elseif ($achados.Count -gt 0 -and -not $SemPerguntar) {
    Diga "  Keep those files before deleting?"
    Diga "  ENTER keeps them in a folder alongside. Type NO to skip."
    $r = Perguntar "  [ENTER = guardar]" ""
    $resp = $r.Trim().ToUpperInvariant()
    if ($resp -ne "NO" -and $resp -ne "NAO") {
        $carimbo = (Get-Date -Format "yyyy-MM-dd_HHmm")
        $guardarEm = Join-Path (Split-Path -Parent $AQUI) `
                     ((Split-Path -Leaf $AQUI) + "_GUARDADO_" + $carimbo)
    }
}

if (-not $SemPerguntar) {
    Diga ""
    Diga "  To confirm, type  UNINSTALL  and press ENTER."
    Diga "  Anything else cancels."
    $c = Perguntar "  >" ""
    $digitado = $c.Trim().ToUpperInvariant()
    if ($digitado -ne "UNINSTALL" -and $digitado -ne "DESINSTALAR") {
        Diga ""
        Diga "  Cancelled. Nothing was deleted."
        exit 2
    }
}

if ($guardarEm) {
    Diga ""
    Diga ("  Guardando em " + $guardarEm)
    New-Item -ItemType Directory -Path $guardarEm -Force | Out-Null
    foreach ($a in $achados) {
        $de = Join-Path $AQUI $a
        try {
            Copy-Item -LiteralPath $de -Destination $guardarEm -Recurse -Force
            Diga ("    " + $a)
        } catch { Diga ("    FALHOU: " + $a + " (" + $_.Exception.Message + ")") }
    }
    Anote ("guardado em " + $guardarEm)
}

if ($apagarFora) {
    Diga ""
    Diga "  Removing what was outside the folder"
    foreach ($f in $FORA) {
        try {
            Remove-Item -LiteralPath $f -Recurse -Force
            Diga ("    " + $f)
        } catch { Diga ("    could not remove (in use?): " + $f) }
    }
    Anote ("fora da pasta: apagado")
}

Diga ""
Diga "  Removing shortcuts"
$alvos = @(
    (Join-Path ([Environment]::GetFolderPath("Desktop")) "Radioterapia.ai Local Suite.lnk"),
    (Join-Path ([Environment]::GetFolderPath("Desktop")) "Auto Contorno - Radioterapia.ai.lnk"),
    (Join-Path ([Environment]::GetFolderPath("Programs")) "Radioterapia.AI")
)
foreach ($a in $alvos) {
    if (Test-Path -LiteralPath $a) {
        try {
            Remove-Item -LiteralPath $a -Recurse -Force
            Diga ("    " + (Split-Path -Leaf $a))
        } catch { Diga ("    nao consegui: " + $a) }
    }
}

$RAIZ = Split-Path -Parent $AQUI
$PROJETO = Split-Path -Leaf $AQUI
$nomesDesta = @($PROJETO)
try {
    foreach ($l in (Get-Content -LiteralPath (Join-Path $AQUI "entrega.txt") -Encoding UTF8)) {
        if ($l -match "^\s*PROJETO\s*=\s*(.+?)\s*$") { $nomesDesta += $Matches[1] }
    }
} catch { }
# GUARDA: regra unica do registro: no PAI da pasta do programa; sai so a
# entrada que aponta para esta pasta (ou que nao diz pasta nenhuma).
$REG = Join-Path $RAIZ "_instalados.json"
if (Test-Path -LiteralPath $REG) {
    try {
        $j = [System.IO.File]::ReadAllText($REG, [System.Text.Encoding]::UTF8) | ConvertFrom-Json
        $novo = @{}
        foreach ($p in $j.PSObject.Properties) {
            $onde = ""
            try { if ($p.Value.caminho) { $onde = [string]$p.Value.caminho } } catch { }
            $desta = ($nomesDesta -contains $p.Name) -and
                     ((-not $onde) -or ($onde.TrimEnd('\') -ieq $AQUI.TrimEnd('\')))
            if (-not $desta) { $novo[$p.Name] = $p.Value }
        }
        [System.IO.File]::WriteAllText($REG,
            ($novo | ConvertTo-Json -Depth 8), (New-Object System.Text.UTF8Encoding($false)))
        Diga ("  " + $PROJETO + " saiu do _instalados.json")
    } catch { Diga "  could not update _instalados.json" }
}

Diga ""
Diga "  Deleting the folder. This can take a minute."
Diga ""
$bat = Join-Path $env:TEMP ("radai_rm_" + (Get-Random) + ".cmd")
$conteudo = @"
@echo off
REM GUARDA: findstr com caminho absoluto; o find do GNU no PATH le o argumento como caminho, e findstr que nao casa encerra a espera.
:esperar
tasklist /FI "PID eq $PID" 2>nul | %SystemRoot%\System32\findstr.exe /C:"$PID" >nul
if not errorlevel 1 (
  ping -n 2 127.0.0.1 >nul
  goto esperar
)
rmdir /s /q "$AQUI"
if exist "$AQUI" (
  echo.
  echo   Something is left in "$AQUI".
  echo   Usually antivirus or an open file. Delete it by hand.
  echo.
  echo   Press any key to close this window.
  pause >nul
) else (
  echo.
  echo   ============================================================
  echo    UNINSTALLED.
  echo   ============================================================
  echo.
  echo   To install again, run START_HERE.cmd from the package.
  echo.
  echo   Press any key to close this window.
  pause >nul
)
del /q "%~f0" >nul 2>&1
"@
[System.IO.File]::WriteAllText($bat, ($conteudo -replace "`r?`n", "`r`n"),
                               (New-Object System.Text.ASCIIEncoding))
if ($env:RADAI_SEM_JANELA) {
    Anote ("removedor destacado ESCRITO e nao disparado (modo de teste): " + $bat)
} else {
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c", $bat -WindowStyle Normal
    Anote "removedor destacado disparado"
}
exit 0
