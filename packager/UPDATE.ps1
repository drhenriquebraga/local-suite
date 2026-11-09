param([string]$Destino = "", [string]$Python = "", [switch]$SemPerguntar,
      [switch]$SoEncerrar, [switch]$SoDecidir, [int]$EsperarPid = 0,
      [switch]$Reabrir, [string]$SinalPronto = "", [string]$ChavePronto = "", [int]$TetoReabrirS = 300)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$AQUI = $PSScriptRoot
if (-not $AQUI) { $AQUI = Split-Path -Parent $MyInvocation.MyCommand.Path }
$PACOTE = Split-Path -Parent $AQUI
if (-not (Test-Path -LiteralPath (Join-Path $PACOTE "app"))) { $PACOTE = $AQUI }

$script:ConsoleExtra = $false
$script:ConsoleDisponivel = $false
try {
    if (-not ('RadaiConsoleAtualizacao' -as [type])) {
        Add-Type -TypeDefinition 'using System; using System.Text; using System.Runtime.InteropServices;
public static class RadaiConsoleAtualizacao {
 [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)] static extern IntPtr CreateFile(string n,uint a,uint s,IntPtr x,uint c,uint f,IntPtr t);
 [DllImport("kernel32.dll")] static extern IntPtr GetStdHandle(int n);
 [DllImport("kernel32.dll")] static extern uint GetFileType(IntPtr h);
 [DllImport("kernel32.dll", CharSet=CharSet.Unicode)] static extern bool WriteConsole(IntPtr h,string t,uint n,out uint w,IntPtr r);
 [DllImport("kernel32.dll", CharSet=CharSet.Unicode)] static extern bool ReadConsole(IntPtr h,StringBuilder t,uint n,out uint w,IntPtr r);
 [DllImport("shell32.dll", CharSet=CharSet.Unicode)] static extern IntPtr CommandLineToArgvW(string t,out int n);
 [DllImport("kernel32.dll")] static extern IntPtr LocalFree(IntPtr p);
 public static string[] Argumentos(string t) { int n; IntPtr p=CommandLineToArgvW(t,out n); if(p==IntPtr.Zero) return new string[0]; try { var a=new string[n]; for(int i=0;i<n;i++) a[i]=Marshal.PtrToStringUni(Marshal.ReadIntPtr(p,i*IntPtr.Size)); return a; } finally { LocalFree(p); } }
 static IntPtr saida=IntPtr.Zero;
 public static bool Abrir() { saida=CreateFile("CONOUT$",0x40000000,3,IntPtr.Zero,3,0,IntPtr.Zero); return saida!=IntPtr.Zero && saida!=new IntPtr(-1); }
 [DllImport("kernel32.dll")] static extern uint GetConsoleProcessList(uint[] p,uint n);
 public static bool Propria() { return GetConsoleProcessList(new uint[2],2)==1; }
 public static bool Redirecionada() { return GetFileType(GetStdHandle(-11))!=2; }
 public static void Escrever(string t) { uint n; WriteConsole(saida,t,(uint)t.Length,out n,IntPtr.Zero); }
 public static string Ler() { IntPtr h=CreateFile("CONIN$",0xC0000000,3,IntPtr.Zero,3,0,IntPtr.Zero); if(h==IntPtr.Zero || h==new IntPtr(-1)) return ""; uint n; var b=new StringBuilder(256); return ReadConsole(h,b,255,out n,IntPtr.Zero) ? b.ToString().Trim() : ""; }
}' | Out-Null
    }
    $script:ConsoleDisponivel = [RadaiConsoleAtualizacao]::Abrir()
    $script:ConsoleExtra = (-not $SoDecidir) -and $script:ConsoleDisponivel -and [RadaiConsoleAtualizacao]::Propria() -and [RadaiConsoleAtualizacao]::Redirecionada()
} catch { }
$script:LogDoAtualizador = ""
$script:LogManual = $script:ConsoleExtra
$script:LogFalhou = $false
function Anote($txt) {
    if (-not $script:LogDoAtualizador) { return }
    try { [IO.File]::AppendAllText($script:LogDoAtualizador, ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + " " + [string]$txt + "`r`n"), [Text.UTF8Encoding]::new($false)) }
    catch { $script:LogFalhou = $true }
}
function Diga($t) {
    # GUARDA: a console propria nunca escreve no stdout herdado do motor.
    if ($script:ConsoleExtra) { [RadaiConsoleAtualizacao]::Escrever(([string]$t + "`r`n")) }
    else { Write-Host $t }
    if ($script:LogManual) { Anote $t }
}
$script:CodigoEmTroca = $false
$script:CodigoCompleto = $false
$script:JaReabriu = $false
$script:ProcessoNovo = $null
$script:MotivoReabrir = ""
$script:ProcessosConferidos = @{}
$script:FalhaConferirProcessos = $false

function UnidadesLocais {
    # GUARDA: a mesma variavel do UNINSTALL.ps1; a bateria simula outro disco sem tocar nos discos de quem a roda.
    if ($env:RADAI_UNIDADES_LOCAIS) {
        return @($env:RADAI_UNIDADES_LOCAIS -split ";" | Where-Object { $_ })
    }
    $r = @()
    foreach ($d in [System.IO.DriveInfo]::GetDrives()) {
        try {
            if (-not $d.IsReady) { continue }
            if ($d.DriveType -ne [System.IO.DriveType]::Fixed) { continue }
            $r += $d.RootDirectory.FullName
        } catch { }
    }
    return $r
}
function PublicarProntidao($pronto, $erro = "") {
    if (-not $SinalPronto) { return $true }
    try {
        $caminhoPronto = [IO.Path]::GetFullPath($SinalPronto)
        if (-not $caminhoPronto.StartsWith(([IO.Path]::GetFullPath($PACOTE).TrimEnd('\') + '\'), [StringComparison]::OrdinalIgnoreCase)) { return $false }
        $dadoPronto = @{pronto=[bool]$pronto;pid=$PID;chave=$ChavePronto;erro=[string]$erro} | ConvertTo-Json -Compress
        [IO.File]::WriteAllText($caminhoPronto, $dadoPronto, [Text.UTF8Encoding]::new($false))
        return $true
    } catch { return $false }
}
function PareCom($t, $codigo) {
    [void](PublicarProntidao $false $t)
    Diga ""
    Diga "============================================================"
    Diga "  A ATUALIZACAO NAO ACONTECEU"
    Diga ""
    foreach ($l in ($t -split "`n")) { Diga ("  " + $l) }
    Diga "============================================================"
    Diga ""
    Sair $codigo
}
function Pare($t) { PareCom $t 1 }

function CriarAtalhos($DESTINO, $RAIZ) {
    # GUARDA: a mesma no INSTALL.ps1 e no UPDATE.ps1, letra a letra; o
    # atalho que a pessoa apagou volta, e o nome antigo sai.
    $alvo = Join-Path $DESTINO "RADIOTERAPIA_AI_LOCAL_SUITE.cmd"
    if (-not (Test-Path -LiteralPath $alvo)) {
        $alvo = Join-Path $DESTINO "ABRIR_AUTO_CONTORNO.cmd"
    }
    if (-not (Test-Path -LiteralPath $alvo)) {
        $alvo = Join-Path $DESTINO "start_watcher.cmd"
    }
    if (-not (Test-Path -LiteralPath $alvo)) {
        Diga "   AVISO: start_watcher.cmd nao veio no pacote; sem atalhos."
        return 0
    }
    $icone = ""
    foreach ($n in @("favicon.ico", "radioterapia_ai.ico")) {
        $c = Join-Path $DESTINO $n
        if (Test-Path -LiteralPath $c) { $icone = $c; break }
    }
    $temIcone = [bool]$icone

    if ($env:RADAI_ATALHOS_NA_RAIZ) {
        $menu = Join-Path $RAIZ "_atalhos_menu"
        $destinos = @(
            @{ pasta = (Join-Path $RAIZ "_atalhos_desktop"); rotulo = "area de trabalho (modo de teste)" },
            @{ pasta = $menu;                                rotulo = "menu Iniciar (modo de teste)" }
        )
    } else {
        $menu = Join-Path ([Environment]::GetFolderPath("Programs")) "Radioterapia.AI"
        $destinos = @(
            @{ pasta = [Environment]::GetFolderPath("Desktop"); rotulo = "area de trabalho" },
            @{ pasta = $menu;                                   rotulo = "menu Iniciar" }
        )
    }

    $feitos = 0
    foreach ($d in $destinos) {
        try {
            if (-not (Test-Path -LiteralPath $d.pasta)) {
                New-Item -ItemType Directory -Path $d.pasta -Force | Out-Null
            }
            $lnk = Join-Path $d.pasta "Radioterapia.ai Local Suite.lnk"

            $antigo = Join-Path $d.pasta "Auto Contorno - Radioterapia.ai.lnk"
            if (Test-Path -LiteralPath $antigo) {
                try { Remove-Item -LiteralPath $antigo -Force } catch { }
            }
            $ws = New-Object -ComObject WScript.Shell
            $s = $ws.CreateShortcut($lnk)
            $s.TargetPath       = $alvo
            $s.WorkingDirectory = $DESTINO
            $s.Description      = "Radioterapia.ai Local Suite (abre em http://127.0.0.1:8777/)"
            if ($temIcone) { $s.IconLocation = ($icone + ',0') }
            $s.Save()
            $feitos++
            Diga ("   " + $d.rotulo + ": " + $lnk)
        } catch {
            Diga ("   AVISO: nao consegui criar o atalho em " + $d.rotulo + ".")
            Anote ("atalho " + $d.rotulo + " falhou: " + $_.Exception.Message)
        }
    }
    if (-not $temIcone) {
        Diga "   (nenhum .ico no pacote: atalhos com o icone padrao)"
        Anote "icone ausente"
    }
    if ($feitos -eq 0) {
        Diga ("   Abra direto: " + $alvo)
    }
    return $feitos
}

$script:PastaAlvo = $Destino
$script:JaReabriu = $false
function ReabrirOApp([switch]$Avulso) {
    if (-not $Reabrir -or ($script:JaReabriu -and -not $Avulso)) { return $false }
    $pasta = $script:PastaAlvo
    if (-not $pasta) { return $false }
    $pyA = $Python
    if (-not $pyA) { $pyA = Join-Path $pasta "python\python.exe" }
    $lanc = Join-Path $pasta "radai_lancador.py"
    if (-not (Test-Path -LiteralPath $pyA) -or -not (Test-Path -LiteralPath $lanc)) {
        $script:MotivoReabrir = "Nao achei o Python ou o lancador da instalacao."
        return $false
    }
    $pR = PortaDaInstalacao $pasta
    $lista = @(('"' + $lanc + '"'), "--url", ("http://127.0.0.1:" + $pR + "/"),
               "--log", ('"' + (Join-Path $pasta "radai_lancador.log") + '"'))
    if (-not $Avulso -and $EsperarPid -gt 0) { $lista += @("--sucessor", [string]$EsperarPid, "--abrir-janela") }
    try {
        $script:ProcessoNovo = Start-Process -FilePath $pyA -ArgumentList $lista -WorkingDirectory $pasta -WindowStyle Hidden -PassThru
        $script:JaReabriu = $true
        Diga "  reabrindo o app em uma janela propria"
        return $true
    } catch {
        $script:MotivoReabrir = $_.Exception.Message
        return $false
    }
}
function PainelNovo($porta, $versao, $antigo) {
    $req = [System.Net.WebRequest]::Create("http://127.0.0.1:" + $porta + "/api/atualizar")
    $req.Proxy = $null
    $req.Timeout = 2000
    $req.Method = "POST"
    $req.ContentType = "application/json"
    $req.Headers.Add("Origin", ("http://127.0.0.1:" + $porta))
    $corpo = [Text.Encoding]::UTF8.GetBytes('{"acao":"estado"}')
    $req.ContentLength = $corpo.Length
    $envio = $req.GetRequestStream()
    try { $envio.Write($corpo, 0, $corpo.Length) } finally { $envio.Dispose() }
    $resp = $req.GetResponse()
    try {
        $leitor = New-Object IO.StreamReader($resp.GetResponseStream())
        try { $d = $leitor.ReadToEnd() | ConvertFrom-Json } finally { $leitor.Dispose() }
    } finally { $resp.Dispose() }
    if ($d.radai -ne $true -or [int]$d.pid -le 0 -or ([int]$antigo -gt 0 -and [int]$d.pid -eq [int]$antigo)) { return $false }
    if (([string]$d.aqui).TrimStart('v') -ne ([string]$versao).TrimStart('v')) {
        $script:MotivoReabrir = "O painel respondeu com outra versao: " + [string]$d.aqui
        return $false
    }
    return ($d.janela_pronta -eq $true)
}
function AguardarPainelNovo($porta, $versao) {
    $inicio = Get-Date
    $fim = $inicio.AddSeconds([Math]::Max(1, $TetoReabrirS))
    $proximaMensagem = $inicio
    while ((Get-Date) -lt $fim) {
        try { if (PainelNovo $porta $versao $EsperarPid) { return $true } } catch { }
        if ($script:MotivoReabrir) { return $false }
        if ($script:ProcessoNovo) {
            try {
                if ($script:ProcessoNovo.HasExited -and $script:ProcessoNovo.ExitCode -ne 0) {
                    $script:MotivoReabrir = "O lancador terminou com codigo " + $script:ProcessoNovo.ExitCode
                    return $false
                }
            } catch { }
        }
        if ((Get-Date) -ge $proximaMensagem) {
            Diga ("  5/5  Esperando o painel da v" + $versao + " abrir... " + [int]((Get-Date)-$inicio).TotalSeconds + " s")
            $proximaMensagem = (Get-Date).AddSeconds(5)
        }
        Start-Sleep -Milliseconds 500
    }
    $script:MotivoReabrir = "O painel da versao nova nao respondeu em " + $TetoReabrirS + " s."
    return $false
}
function Sair($codigo) {
    if ($Reabrir) {
        if ($codigo -eq 0) {
            Diga "  esta janela fecha sozinha em 5 s"
            Start-Sleep -Seconds 5
        } else {
            if ($script:CodigoEmTroca -and -not $script:CodigoCompleto) {
                Diga "  A copia nao terminou. Nao abra uma instalacao parcialmente atualizada."
                Diga "  Corrija o motivo acima e execute este instalador novamente."
            } else {
                Diga "  O aplicativo pode ser reaberto pelo atalho da area de trabalho."
            }
            if ($script:LogFalhou -or -not $script:LogDoAtualizador) { Diga "  Nao consegui gravar o log; copie a mensagem desta janela." }
            else { Diga "  O diagnostico esta em radai_atualizar.log na pasta do programa." }
            $naoInterativo = [Environment]::GetCommandLineArgs() -contains '-NonInteractive'
            if ($script:ConsoleDisponivel -and -not $naoInterativo) {
                if (-not $script:CodigoEmTroca -or $script:CodigoCompleto) {
                    Diga "  R + Enter: reabrir o aplicativo. Enter: fechar esta janela."
                    $resposta = [RadaiConsoleAtualizacao]::Ler()
                    if ($resposta -match '^[Rr]$') { [void](ReabrirOApp -Avulso) }
                } else {
                    Diga "  Pressione Enter para fechar esta janela."
                    [void][RadaiConsoleAtualizacao]::Ler()
                }
            }
        }
    }
    exit $codigo
}

trap {
    [void](PublicarProntidao $false $_.Exception.Message)
    Diga ""
    Diga ("  ERRO: " + $_.Exception.Message)
    Sair 1
}

function PortaDaInstalacao($pasta) {
    $p = 8777
    try {
        $cfg = Join-Path $pasta "radai_watcher.config"
        if (Test-Path -LiteralPath $cfg) {
            foreach ($l in (Get-Content -LiteralPath $cfg -Encoding UTF8)) {
                if ($l -match "^[\s\uFEFF]*PORT\s*=\s*(\d+)") { $p = [int]$Matches[1] }
            }
        }
    } catch { }
    return $p
}

function PortaViva($p) {
    try {
        $s = New-Object System.Net.Sockets.TcpClient
        $s.Connect("127.0.0.1", $p)
        $v = $s.Connected
        $s.Close()
        return $v
    } catch { return $false }
}

function EONossoPainel($p) {
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

function PedirParaEncerrar($p) {
    try {
        $req = [System.Net.WebRequest]::Create("http://127.0.0.1:" + $p + "/api/encerrar")
        # GUARDA: sem Proxy nulo o pedido ao 127.0.0.1 vai ao proxy do Windows.
        $req.Proxy = $null
        $req.Method = "POST"
        $req.ContentType = "application/json"
        $req.Timeout = 5000
        $corpo = [System.Text.Encoding]::UTF8.GetBytes('{"modo":"tudo"}')
        $req.ContentLength = $corpo.Length
        $s = $req.GetRequestStream()
        $s.Write($corpo, 0, $corpo.Length)
        $s.Close()
        $req.GetResponse().Close()
        return $true
    } catch { return $false }
}

function _Prefixo($pasta) {
    try { $c = [System.IO.Path]::GetFullPath($pasta) } catch { $c = [string]$pasta }
    return ($c.TrimEnd('\') + '\')
}

function PythonDaPasta($p, $pasta) {
    if (-not $p) { return $false }
    $nome = ([string]$p.Name).ToLower()
    if ($nome -ne "python.exe" -and $nome -ne "pythonw.exe") { return $false }
    $exe = [string]$p.ExecutablePath
    return ($exe -and $exe.StartsWith((_Prefixo $pasta), [StringComparison]::OrdinalIgnoreCase))
}
function SeloDoProcesso($p) {
    if (-not $p -or -not $p.CreationDate) { return "" }
    try { return ([datetime]$p.CreationDate).ToUniversalTime().Ticks.ToString() } catch { return "" }
}
function EntradaDoApp($p, $pasta) {
    if (-not (PythonDaPasta $p $pasta)) { return $false }
    try { $argumentos = [RadaiConsoleAtualizacao]::Argumentos([string]$p.CommandLine) } catch { return $false }
    for ($i = 1; $i -lt $argumentos.Length; $i++) {
        $a = [string]$argumentos[$i]
        if ($a -eq '-c' -or $a -eq '-m' -or $a -eq '-') { return $false }
        if ($a -eq '-X' -or $a -eq '-W' -or $a -eq '--check-hash-based-pycs') { $i++; continue }
        if ($a.StartsWith('-')) { continue }
        if (-not [IO.Path]::IsPathRooted($a)) { return $false }
        try { $entrada = [IO.Path]::GetFullPath($a) } catch { return $false }
        foreach ($nome in @('radai_watcher.py', 'radai_lancador.py')) {
            if ($entrada.Equals([IO.Path]::GetFullPath((Join-Path $pasta $nome)), [StringComparison]::OrdinalIgnoreCase)) { return $true }
        }
        return $false
    }
    return $false
}
function ProcessoDaPasta($id, $pasta) {
    # GUARDA: runtime compartilhado nao prova propriedade. Exige entrada
    # absoluta do app ou descendencia conferida, com PID e criacao iguais.
    try { $p = Get-CimInstance Win32_Process -Filter ("ProcessId=" + [int]$id) -ErrorAction Stop } catch { return $false }
    if (-not (PythonDaPasta $p $pasta)) { return $false }
    $selo = SeloDoProcesso $p
    if (-not $selo) { return $false }
    if (EntradaDoApp $p $pasta) { return $true }
    $d = $script:ProcessosConferidos[[int]$id]
    return ($d -and $d.selo -eq $selo -and $d.pasta -eq (_Prefixo $pasta))
}

function EstadoDoMotor($porta) {
    if (-not $env:LOCALAPPDATA) { return "" }
    return (Join-Path (Join-Path $env:LOCALAPPDATA "RADIOTERAPIA_AI") ("motor_" + $porta + ".json"))
}

function ProcessosDoApp($pasta, $porta) {
    $script:FalhaConferirProcessos = $false
    try { $todos = @(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" -ErrorAction Stop) }
    catch { $script:FalhaConferirProcessos = $true; return @() }
    $nossos = @{}
    foreach ($p in $todos) {
        if (-not (PythonDaPasta $p $pasta)) { continue }
        $idp = [int]$p.ProcessId
        $selo = SeloDoProcesso $p
        if (-not $selo) { continue }
        $d = $script:ProcessosConferidos[$idp]
        if (EntradaDoApp $p $pasta) { $nossos[$idp] = $p }
        elseif ($d -and $d.selo -eq $selo -and $d.pasta -eq (_Prefixo $pasta)) { $nossos[$idp] = $p }
        elseif ($d) { $script:ProcessosConferidos.Remove($idp) }
    }
    do {
        $mudou = $false
        foreach ($p in $todos) {
            $idp = [int]$p.ProcessId
            if ($nossos.ContainsKey($idp) -or -not (PythonDaPasta $p $pasta)) { continue }
            if ($nossos.ContainsKey([int]$p.ParentProcessId) -and (SeloDoProcesso $p)) {
                $pai = $nossos[[int]$p.ParentProcessId]
                if ([datetime]$p.CreationDate -ge [datetime]$pai.CreationDate) { $nossos[$idp] = $p; $mudou = $true }
            }
        }
    } while ($mudou)
    foreach ($idp in $nossos.Keys) {
        $script:ProcessosConferidos[$idp] = @{selo=(SeloDoProcesso $nossos[$idp]);pasta=(_Prefixo $pasta)}
    }
    return @($nossos.Keys | Sort-Object)
}

function EsperarSumir($ids, $pasta, $segundos) {
    $fim = (Get-Date).AddSeconds($segundos)
    do {
        $vivos = @($ids | Where-Object { ProcessoDaPasta $_ $pasta })
        if ($vivos.Count -eq 0) { return }
        Start-Sleep -Milliseconds 300
    } while ((Get-Date) -lt $fim)
    return $vivos
}

function MarcarMotorEncerrado($porta, $ids) {
    $est = EstadoDoMotor $porta
    if (-not $est -or -not (Test-Path -LiteralPath $est -PathType Leaf)) { return }
    try {
        $j = [System.IO.File]::ReadAllText($est, [System.Text.Encoding]::UTF8) | ConvertFrom-Json
        if ([string]$j.estado -ne "rodando" -or ($ids -notcontains [int]$j.pid)) { return }
        $novo = '{"estado": "encerrado", "pid": ' + [int]$j.pid + ', "hora": "' +
                (Get-Date -Format "yyyy-MM-dd HH:mm:ss") + '", "por": "atualizador"}'
        [System.IO.File]::WriteAllText($est, $novo, (New-Object System.Text.UTF8Encoding($false)))
    } catch { }
}

function EncerrarOApp($pasta) {
    $porta = PortaDaInstalacao $pasta
    $ids = @(ProcessosDoApp $pasta $porta)
    if ($script:FalhaConferirProcessos) { $script:PidsQueFicaram = @("identidade nao conferida"); return "resistiu" }
    if ($ids.Count -eq 0) { return "nada" }
    Diga ("  o app esta aberto nesta pasta (PID " + ($ids -join ", ") + "): encerrando")
    if ((PortaViva $porta) -and (EONossoPainel $porta)) {
        if (PedirParaEncerrar $porta) {
            Diga "  pedi ao app que feche, como o Fechar tudo da engrenagem"
            $vivos = @(EsperarSumir $ids $pasta 30)
        }
    }
    $aForca = @()
    for ($rodada = 0; $rodada -lt 3; $rodada++) {
        $agora = @(ProcessosDoApp $pasta $porta)
        if ($script:FalhaConferirProcessos) { $script:PidsQueFicaram = @("identidade nao conferida"); return "resistiu" }
        if ($agora.Count -eq 0) { break }
        foreach ($i in $agora) {
            if (-not (ProcessoDaPasta $i $pasta)) { continue }
            try {
                $processoAlvo = Get-Process -Id $i -ErrorAction Stop
                $null = $processoAlvo.Handle
                if (-not (ProcessoDaPasta $i $pasta)) { continue }
                $conferido = $script:ProcessosConferidos[[int]$i]
                if (-not $conferido -or [Math]::Abs($processoAlvo.StartTime.ToUniversalTime().Ticks - [long]$conferido.selo) -ge 10000) { continue }
                Stop-Process -InputObject $processoAlvo -Force -ErrorAction Stop
                $aForca += $i
                Diga ("  encerrado a forca: PID " + $i)
            } catch {
                Diga ("  nao consegui encerrar o PID " + $i + " (" + $_.Exception.Message + ")")
            }
        }
        $vivos = @(EsperarSumir $agora $pasta 10)
    }
    if ($aForca.Count -gt 0) { MarcarMotorEncerrado $porta $aForca }
    $resto = @(ProcessosDoApp $pasta $porta)
    if ($script:FalhaConferirProcessos) { $script:PidsQueFicaram = @("identidade nao conferida"); return "resistiu" }
    if ($resto.Count -gt 0) {
        $script:PidsQueFicaram = $resto
        Diga ("  continua aberto: PID " + ($resto -join ", "))
        return "resistiu"
    }
    Diga ("  app encerrado (PID " + ($ids -join ", ") + "); sigo")
    return "encerrado"
}

if ($SoEncerrar) {
    if (-not $Destino -or -not (Test-Path -LiteralPath (Join-Path $Destino "radai_watcher.py"))) {
        Diga "  nenhuma instalacao nesta pasta: nada a encerrar"
        exit 0
    }
    $r = EncerrarOApp $Destino
    if ($r -eq "resistiu") { exit 4 }
    $pE = PortaDaInstalacao $Destino
    if (PortaViva $pE) {
        if (EONossoPainel $pE) {
            Diga ("  a porta " + $pE + " ainda responde o painel do Local Suite, de um")
            Diga "  processo que nao e desta pasta ou que nao consegui conferir"
            exit 4
        }
        Diga ("  a porta " + $pE + " esta com outro programa, que nao e o app: nao mexo nele")
    }
    if ($r -eq "nada") { Diga "  o app nao esta aberto nesta pasta" }
    exit 0
}

if ($Reabrir) {
    try { $Host.UI.RawUI.WindowTitle = "Radioterapia.ai Local Suite - atualizando" } catch { }
    if ($Destino -and (Test-Path -LiteralPath $Destino -PathType Container)) {
        $logA = Join-Path $Destino "radai_atualizar.log"
        $script:LogDoAtualizador = $logA
        try {
            if ((Test-Path -LiteralPath $logA) -and ((Get-Item -LiteralPath $logA).Length -gt 1MB)) {
                Remove-Item -LiteralPath $logA -Force
            }
            if (-not $script:ConsoleExtra) { Start-Transcript -Path $logA -Append | Out-Null }
        } catch { $script:LogManual = $true }
    }
}

Diga "============================================================"
Diga "  Radioterapia.ai Local Suite - atualizar"
Diga "============================================================"
Diga ""

foreach ($p in @("app", "tools", "entrega.txt")) {
    if (-not (Test-Path -LiteralPath (Join-Path $PACOTE $p))) {
        Pare ("Este pacote esta incompleto: falta " + $p + [char]10 +
              "Extraia o .zip inteiro e rode o START_HERE.cmd de la," + [char]10 +
              "botao Instalar / Atualizar app nesta maquina.")
    }
}
$VERSAO_NOVA = ""
$PROJETO_NOVO = ""
foreach ($l in (Get-Content -LiteralPath (Join-Path $PACOTE "entrega.txt") -Encoding UTF8)) {
    if ($l -match "^\s*VERSAO\s*=\s*(.+?)\s*$") { $VERSAO_NOVA = $Matches[1] }
    if ($l -match "^\s*PROJETO\s*=\s*(.+?)\s*$") { $PROJETO_NOVO = $Matches[1] }
}
Diga "  1/5  Conferindo o pacote e a instalacao..."
Diga ("  pacote:  versao " + $VERSAO_NOVA)

$achados = @()
if ($Destino) {
    if (Test-Path -LiteralPath (Join-Path $Destino "radai_watcher.py")) {
        $achados += $Destino
    }
} else {
    foreach ($u in @(UnidadesLocais)) {
        try {
            $raiz = Join-Path $u "RADIOTERAPIA_AI"
            $reg = Join-Path $raiz "_instalados.json"
            if (Test-Path -LiteralPath $reg) {
                $j = [System.IO.File]::ReadAllText($reg, [System.Text.Encoding]::UTF8) | ConvertFrom-Json
                foreach ($p in $j.PSObject.Properties) {
                    $cands = @()
                    try { if ($p.Value.caminho) { $cands += [string]$p.Value.caminho } } catch { }
                    $cands += (Join-Path $raiz $p.Name)
                    foreach ($c in $cands) {
                        if (Test-Path -LiteralPath (Join-Path $c "radai_watcher.py")) {
                            $achados += $c; break
                        }
                    }
                }
            }
            if (Test-Path -LiteralPath $raiz -PathType Container) {
                foreach ($sub in (Get-ChildItem -LiteralPath $raiz -Directory -ErrorAction SilentlyContinue)) {
                    if ((Test-Path -LiteralPath (Join-Path $sub.FullName "radai_watcher.py")) -and
                        (Test-Path -LiteralPath (Join-Path $sub.FullName "entrega.txt"))) {
                        $achados += $sub.FullName
                    }
                }
            }
        } catch { }
    }
}
$achados = @($achados | Select-Object -Unique)
if ($achados.Count -eq 0) {
    Pare ("Nao achei nenhuma instalacao nesta maquina." + [char]10 + [char]10 +
          "Se o programa esta noutra pasta, chame com o caminho:" + [char]10 +
          "  UPDATE.ps1 -Destino D:\Radioterapia_AI\LOCAL_SUITE" + [char]10 + [char]10 +
          "Ou abra o START_HERE.cmd e clique em ATUALIZAR: ele pede a" + [char]10 +
          "pasta quando nao acha sozinho." + [char]10 + [char]10 +
          "Para INSTALAR do zero, use o START_HERE.cmd deste pacote." + [char]10 +
          "Atualizar o que nao existe copiaria codigo sem runtime, e o" + [char]10 +
          "erro so apareceria na primeira serie da noite.")
}
$INST = $achados[0]
$script:PastaAlvo = $INST
if ($achados.Count -gt 1) {
    Diga "  achei mais de uma instalacao:"
    foreach ($a in $achados) { Diga ("    " + $a) }
    Diga ("  usando a primeira: " + $INST)
}
$VERSAO_VELHA = "(desconhecida)"
$ent = Join-Path $INST "entrega.txt"
if (Test-Path -LiteralPath $ent) {
    foreach ($l in (Get-Content -LiteralPath $ent -Encoding UTF8)) {
        if ($l -match "^\s*VERSAO\s*=\s*(.+?)\s*$") { $VERSAO_VELHA = $Matches[1] }
    }
}
Diga ("  instalado: versao " + $VERSAO_VELHA + "  em  " + $INST)
Diga ""

$py = $Python
if (-not $py) { $py = Join-Path $INST "python\python.exe" }
if (-not (Test-Path -LiteralPath $py)) { $py = "" }
$decisor = Join-Path $PACOTE "build\requisitos.py"
if (-not (Test-Path -LiteralPath $decisor)) {
    Pare ("Este pacote nao traz o build\requisitos.py, que e quem decide" + [char]10 +
          "se a atualizacao pode ser offline. Pacote incompleto.")
}
if (-not $py) {
    Pare ("Nao achei o Python da instalacao (" + $INST + "\python\python.exe)." + [char]10 +
          "Sem ele nao da para comparar os requisitos, e comparar e o que" + [char]10 +
          "separa 'copia de codigo' de 'precisa de internet'.")
}

$script = @'
import json, os, sys
sys.path.insert(0, sys.argv[1])
import requisitos as R
pacote = R.calcular(sys.argv[2])
instalado = R.ler(sys.argv[3])
pode, motivos = R.comparar(instalado, pacote)
print(json.dumps({"pode": pode, "motivos": motivos}, ensure_ascii=False))
'@
$tmp = Join-Path $env:TEMP ("radai_decidir_" + (Get-Random) + ".py")
[System.IO.File]::WriteAllText($tmp, $script, (New-Object System.Text.UTF8Encoding($false)))
$saida = ""
try {
    $saida = & $py $tmp (Join-Path $PACOTE "build") $PACOTE $INST 2>&1 | Out-String
} catch {
    $saida = ""
} finally {
    Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
}
$pode = $false
$motivos = @()
$linha = ($saida -split "`n" | Where-Object { $_.Trim().StartsWith("{") } |
          Select-Object -Last 1)
if (-not $linha) {
    Pare ("Nao consegui decidir se a atualizacao pode ser offline." + [char]10 +
          "Quem decide e o Python da instalacao:" + [char]10 +
          "  " + $py + [char]10 + [char]10 +
          "Saida dele:" + [char]10 + $saida.Trim())
}
try {
    $j = $linha | ConvertFrom-Json
    $pode = [bool]$j.pode
    $motivos = @($j.motivos)
} catch {
    Pare ("A resposta do decisor nao e JSON valido:" + [char]10 + $linha)
}

if ($SoDecidir) {
    # GUARDA: contrato com o botao Atualizar agora do app: 0 so o codigo,
    # 3 precisa de pacote novo; nada e encerrado nem copiado neste modo.
    if ($pode) { Diga "DECISAO=codigo" } else { Diga "DECISAO=pacote" }
    foreach ($m in $motivos) { Diga ("MOTIVO=" + $m) }
    if ($pode) { exit 0 }
    exit 3
}

if (-not $pode) {
    Diga "  ESTA ATUALIZACAO PRECISA DE INTERNET"
    Diga ""
    Diga "  Mudou o que a estacao nao tem como baixar sozinha:"
    foreach ($m in $motivos) { Diga ("    - " + $m) }
    Diga ""
    Diga "  O CAMINHO: o botao Instalar / Atualizar app nesta maquina, do"
    Diga "    START_HERE.cmd, segue sozinho."
    Diga "    Com internet nesta maquina, ele atualiza tudo na pasta instalada."
    Diga "    Sem internet aqui, ele pede o .zip de um pacote completo:"
    Diga "    1. Leve este instalador para uma maquina COM internet"
    Diga "    2. Rode o START_HERE.cmd e escolha"
    Diga "         Maquina com internet: montar um pacote para levar para a maquina offline"
    Diga "    3. Traga o .zip que sair, rode aqui o START_HERE.cmd e clique"
    Diga "         Instalar / Atualizar app nesta maquina"
    Diga ""
    Diga "  A instalacao atual continua funcionando. Nada foi alterado."
    Diga ""
    Sair 3
}

Diga "  Da para atualizar AQUI: so o codigo mudou."
Diga "  Sem internet, sem administrador."
Diga ""

$novos = 0
$trocados = 0
function _Relativos($de, $so) {
    $fora = @()
    if (-not (Test-Path -LiteralPath $de)) { return $fora }
    $raiz = (Resolve-Path -LiteralPath $de).Path.TrimEnd('\')
    foreach ($f in (Get-ChildItem -LiteralPath $de -File -Recurse -ErrorAction SilentlyContinue)) {
        if ($so -and ($f.Extension -notin $so)) { continue }
        if ($f.FullName -like '*\__pycache__\*') { continue }
        $rel = $f.FullName.Substring($raiz.Length).TrimStart('\')
        $fora += @{ f = $f; rel = $rel }
    }
    return $fora
}

function Copiar($de, $para, $so) {
    $n = 0; $t = 0
    foreach ($it in (_Relativos $de $so)) {
        if (($it.rel -split "[\\/]")[0] -ieq "Plugins") { throw "A atualizacao base nao pode alterar Plugins." }
        $alvo = Join-Path $para $it.rel
        if (-not (Test-Path -LiteralPath $alvo)) { $n++ }
        elseif ((Get-Item -LiteralPath $alvo).Length -ne $it.f.Length -or
                (Get-Item -LiteralPath $alvo).LastWriteTimeUtc -ne $it.f.LastWriteTimeUtc) { $t++ }
    }
    return @($n, $t)
}
$EXT_APP   = @(".py", ".cmd", ".ico", ".png", ".svg", ".json", ".js", ".ttf")
$EXT_TOOLS = @(".py")

$DOCUMENTOS = @("NOTICE", "LICENSE")
function ContarAvulsos($de, $para, $nomes) {
    $n = 0; $t = 0
    foreach ($nm in $nomes) {
        $o = Join-Path $de $nm
        if (-not (Test-Path -LiteralPath $o -PathType Leaf)) { continue }
        $a = Join-Path $para $nm
        if (-not (Test-Path -LiteralPath $a)) { $n++ }
        elseif ((Get-Item -LiteralPath $a).Length -ne (Get-Item -LiteralPath $o).Length -or
                (Get-Item -LiteralPath $a).LastWriteTimeUtc -ne (Get-Item -LiteralPath $o).LastWriteTimeUtc) { $t++ }
    }
    return @($n, $t)
}

$r1 = Copiar (Join-Path $PACOTE "app") $INST $EXT_APP
$r2 = Copiar (Join-Path $PACOTE "tools") (Join-Path $INST "tools") $EXT_TOOLS
$r3 = ContarAvulsos $PACOTE $INST $DOCUMENTOS
$novos = $r1[0] + $r2[0] + $r3[0]
$trocados = $r1[1] + $r2[1] + $r3[1]
Diga ("  " + $novos + " arquivo(s) novo(s), " + $trocados + " atualizado(s)")
Diga ("  acompanham o codigo: entrega.txt, _requisitos.json, " + ($DOCUMENTOS -join ", "))
Diga ""
Diga "  NAO sera tocado: radai_watcher.config, _dados.txt, calibracao\, *.log"
Diga ""

if (-not $SemPerguntar) {
    $c = ""
    try { $c = Read-Host "  Atualizar? (S/N)" } catch { $c = "" }
    if ($c.Trim().ToUpper() -ne "S") {
        Diga ""
        Diga "  Cancelado. Nada foi alterado."
        exit 2
    }
}

$porta = PortaDaInstalacao $INST
Diga "  2/5  Conferindo gravacao antes de fechar o app..."
$fontesDaCopia = @(_Relativos (Join-Path $PACOTE "app") $EXT_APP) + @(_Relativos (Join-Path $PACOTE "tools") $EXT_TOOLS)
foreach ($grupo in @(@((Join-Path $PACOTE "app"), $INST, $EXT_APP), @((Join-Path $PACOTE "tools"), (Join-Path $INST "tools"), $EXT_TOOLS))) {
    foreach ($item in (_Relativos $grupo[0] $grupo[2])) {
        $alvoTeste = Join-Path $grupo[1] $item.rel
        if (Test-Path -LiteralPath $alvoTeste -PathType Leaf) {
            $testeAcesso = [IO.File]::Open($alvoTeste, [IO.FileMode]::Open, [IO.FileAccess]::ReadWrite, [IO.FileShare]::ReadWrite)
            $testeAcesso.Dispose()
        }
    }
}
$provaEscrita = Join-Path $INST ("._radai_atualizar_" + [Guid]::NewGuid().ToString('N') + ".tmp")
try { $testeAcesso = [IO.File]::Open($provaEscrita, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write); $testeAcesso.Dispose() }
finally { if (Test-Path -LiteralPath $provaEscrita) { Remove-Item -LiteralPath $provaEscrita -Force } }
foreach ($nomeAvulso in (@('entrega.txt', '_requisitos.json') + $DOCUMENTOS)) {
    $alvoAvulso = Join-Path $INST $nomeAvulso
    if (Test-Path -LiteralPath $alvoAvulso -PathType Leaf) {
        $testeAcesso = [IO.File]::Open($alvoAvulso, [IO.FileMode]::Open, [IO.FileAccess]::ReadWrite, [IO.FileShare]::ReadWrite)
        $testeAcesso.Dispose()
    }
}
[void](ProcessosDoApp $INST (PortaDaInstalacao $INST))
if ($script:FalhaConferirProcessos) { Pare "Nao consegui conferir os processos do app. Nenhum processo sera encerrado nem arquivo trocado." }
if ($SinalPronto -and -not (PublicarProntidao $false)) { Pare "Nao consegui gravar a prontidao do atualizador; o app nao sera encerrado e nenhum arquivo sera trocado." }
if ($Reabrir) {
    $janelaNova = Join-Path $PACOTE "app\radai_janela.py"
    if (Test-Path -LiteralPath $janelaNova -PathType Leaf) {
        try {
            Diga "  Fechando somente as janelas do perfil proprio do Local Suite..."
            $resultadoJanela = & $py $janelaNova --fechar-para-atualizar 2>&1 | Out-String
            Diga ("  " + $resultadoJanela.Trim())
            $fechamentoJanela = $resultadoJanela.Trim() | ConvertFrom-Json
            if ($fechamentoJanela.ok -ne $true) { Pare "A janela propria do app nao fechou. Resolva o aviso nela e tente novamente; nenhum arquivo foi trocado." }
        } catch { Pare "Nao consegui conferir o fechamento da janela propria. Nenhum arquivo foi trocado." }
    }
}
if ($SinalPronto) {
    $prontoNormal = [IO.Path]::GetFullPath($SinalPronto)
    if (-not $prontoNormal.StartsWith(([IO.Path]::GetFullPath($PACOTE).TrimEnd('\') + '\'), [StringComparison]::OrdinalIgnoreCase)) { Pare "Sinal de prontidao fora do pacote." }
    if (-not (PublicarProntidao $true)) { Pare "Nao consegui confirmar a prontidao; nenhum arquivo sera trocado." }
}
Diga "  2/5  Encerrando o motor antigo..."
if ($EsperarPid -gt 0) {
    # GUARDA: o app que pediu a atualizacao fecha sozinho, sem o Fechar tudo;
    # so se ele nao fechar em 2 min o encerramento abaixo entra.
    Diga ("  esperando o app fechar (PID " + $EsperarPid + ")...")
    $inicioEspera = Get-Date
    $proximoAviso = $inicioEspera.AddSeconds(5)
    $fimEspera = $inicioEspera.AddSeconds(120)
    while ((Get-Process -Id $EsperarPid -ErrorAction SilentlyContinue) -and ((Get-Date) -lt $fimEspera)) {
        if ((Get-Date) -ge $proximoAviso) {
            Diga ("  Ainda encerrando o motor antigo... " + [int]((Get-Date)-$inicioEspera).TotalSeconds + " s")
            $proximoAviso = (Get-Date).AddSeconds(5)
        }
        Start-Sleep -Milliseconds 300
    }
    if (Get-Process -Id $EsperarPid -ErrorAction SilentlyContinue) {
        if ($SinalPronto) { PareCom "O app ainda esta aberto. Nenhum arquivo foi trocado; tente novamente depois de concluir o encerramento." 4 }
        Diga "  o app nao fechou sozinho em 2 min: sigo pelo encerramento"
    } else {
        Diga "  o app fechou"
    }
}
while ($true) {
    $enc = EncerrarOApp $INST
    if ($enc -ne "resistiu") { break }
    if ($SemPerguntar) {
        PareCom ("Nao consegui encerrar o app aberto nesta pasta (PID " +
                 ($script:PidsQueFicaram -join ", ") + ")." + [char]10 +
                 "Feche-o pela engrenagem (Fechar, Fechar tudo) ou pelo" + [char]10 +
                 "Gerenciador de Tarefas e rode de novo." + [char]10 + [char]10 +
                 "Trocar o codigo por baixo de um processo em execucao deixa" + [char]10 +
                 "metade dele com a versao velha ate alguem reiniciar.") 4
    }
    $c = ""
    try { $c = Read-Host "  Nao consegui encerrar o app. Feche-o e tente de novo? (S/N)" } catch { $c = "" }
    if ($c.Trim().ToUpper() -ne "S") {
        Diga ""
        Diga "  Cancelado. Nada foi alterado."
        exit 4
    }
}
$viva = PortaViva $porta
if ($viva) {
    if (EONossoPainel $porta) {
        Pare ("O Radioterapia.AI Local Suite esta RODANDO na porta " + $porta + "," + [char]10 +
              "e nao achei o processo dele nesta pasta para encerrar." + [char]10 +
              "Ele roda sem janela: abra o painel (http://127.0.0.1:" + $porta + "/)," + [char]10 +
              "clique em FECHAR APP > Fechar tudo e rode este arquivo de novo." + [char]10 + [char]10 +
              "Trocar o codigo por baixo de um processo em execucao deixa" + [char]10 +
              "metade dele com a versao velha ate alguem reiniciar.")
    }
    Pare ("Alguem esta atendendo na porta " + $porta + ", que e a deste" + [char]10 +
          "programa (chave PORT do radai_watcher.config), e nao responde" + [char]10 +
          "como o painel do Local Suite." + [char]10 + [char]10 +
          "Se o Local Suite estiver travado, feche o python.exe dele no" + [char]10 +
          "Gerenciador de Tarefas e rode de novo. Se for outro programa," + [char]10 +
          "feche-o, ou troque o PORT no radai_watcher.config." + [char]10 + [char]10 +
          "Trocar o codigo por baixo de um processo em execucao deixa" + [char]10 +
          "metade dele com a versao velha ate alguem reiniciar.")
}

Diga ""
Diga "  3/5  Copiando..."
$script:ArquivosCopiados = 0
$script:TotalArquivos = $fontesDaCopia.Count
$script:CachesDoCodigo = @{}
$script:CodigoEmTroca = $true
function Aplicar($de, $para, $so) {
    if (-not (Test-Path -LiteralPath $para)) {
        New-Item -ItemType Directory -Path $para -Force | Out-Null
    }
    foreach ($it in (_Relativos $de $so)) {
        if (($it.rel -split "[\\/]")[0] -ieq "Plugins") { throw "A atualizacao base nao pode alterar Plugins." }
        $alvo = Join-Path $para $it.rel
        $pasta = Split-Path -Parent $alvo
        if ($pasta -and -not (Test-Path -LiteralPath $pasta)) {
            New-Item -ItemType Directory -Path $pasta -Force | Out-Null
        }
        Copy-Item -LiteralPath $it.f.FullName -Destination $alvo -Force
        $script:ArquivosCopiados++
        if ($script:ArquivosCopiados -eq 1 -or $script:ArquivosCopiados % 20 -eq 0 -or $script:ArquivosCopiados -eq $script:TotalArquivos) {
            Diga ("  Arquivos atualizados: " + $script:ArquivosCopiados + "/" + $script:TotalArquivos)
        }
        if ($it.f.Extension -eq '.py') { $script:CachesDoCodigo[(Join-Path (Split-Path -Parent $alvo) '__pycache__')] = $true }
    }
}
Aplicar (Join-Path $PACOTE "app") $INST $EXT_APP
Aplicar (Join-Path $PACOTE "tools") (Join-Path $INST "tools") $EXT_TOOLS

Diga "  Limpando somente os caches dos arquivos de codigo atualizados..."
foreach ($cacheCodigo in $script:CachesDoCodigo.Keys) {
    $cacheNormal = [IO.Path]::GetFullPath($cacheCodigo)
    if (-not $cacheNormal.StartsWith(([IO.Path]::GetFullPath($INST).TrimEnd('\') + '\'), [StringComparison]::OrdinalIgnoreCase)) { Pare "Cache fora da instalacao." }
    if (Test-Path -LiteralPath $cacheNormal -PathType Container) { Remove-Item -LiteralPath $cacheNormal -Recurse -Force -ErrorAction SilentlyContinue }
}

function HashCodigoNeuroLegado([string]$arquivo) {
    $algoritmo = [Security.Cryptography.SHA256]::Create()
    $leitor = [IO.File]::OpenRead($arquivo)
    try { return ([BitConverter]::ToString($algoritmo.ComputeHash($leitor))).Replace('-', '').ToLowerInvariant() }
    finally { $leitor.Dispose(); $algoritmo.Dispose() }
}
foreach ($nomeNeuroLegado in @("radai_nidus.py", "radai_nidus_screen.py")) {
    $fonteNeuroLegado = Join-Path $INST $nomeNeuroLegado
    if (Test-Path -LiteralPath $fonteNeuroLegado -PathType Leaf) {
        $hashNeuroLegado = (HashCodigoNeuroLegado $fonteNeuroLegado)
        $pastaNeuroBackup = Join-Path $INST ".migration-backups\neuro-rt-v1"
        New-Item -ItemType Directory -Path $pastaNeuroBackup -Force | Out-Null
        $arquivoNeuroBackup = Join-Path $pastaNeuroBackup ($hashNeuroLegado + "-" + $nomeNeuroLegado)
        if (-not (Test-Path -LiteralPath $arquivoNeuroBackup)) {
            Copy-Item -LiteralPath $fonteNeuroLegado -Destination $arquivoNeuroBackup -ErrorAction Stop
        }
        if ((HashCodigoNeuroLegado $arquivoNeuroBackup) -ne $hashNeuroLegado) {
            throw "Backup do modulo legado Nidus nao confere; remocao interrompida."
        }
    }
}

$ORFAOS = @(
    "radai_nidus.py",
    "radai_nidus_screen.py",
    "radai_calibrator.py",
    "radai_compiler.py",
    "radai_crosscheck.py",
    "radai_studio.py",
    "tools\test_calibrator.py",
    "maintenance\verify.cmd",
    "ferramentas\iniciar_vigia.cmd",
    "ferramentas\abrir_janela.cmd",
    "iniciar_motor.cmd",
    "ferramentas\iniciar_motor.cmd",
    "launchers\start_engine.cmd",
    "radai_breast.py",
    "radai_anatomy_base.py",
    "docs\literature\anatomy_base.json",
    "radai_corpus.py",
    "radai_deface.py",
    "radai_delivery_tps.py",
    "radai_demo.py",
    "radai_internal.py",
    "radai_nninteractive.py",
    "radai_pelvis.py",
    "radai_png.py",
    "radai_policy.py",
    "radai_reference.py",
    "radai_roadmap.py",
    "radai_suggestion.py",
    "radai_suite.py",
    "radai_thorax.py",
    "radai_thorax_screen.py",
    "radai_thorax_session.py",
    "radai_training.py",
    "radai_wanted.py",
    "radai_weights.py",
    "data\results_all_classes_v1.json",
    "data\results_all_classes_mr.json",
    "tools\test_breast.py",
    "tools\test_anatomy_base.py",
    "tools\test_corpus.py",
    "tools\test_deface.py",
    "tools\test_pelvis.py",
    "tools\test_thorax.py",
    "tools\test_training.py",
    "tools\test_wanted.py",
    "tools\demos.py",
    "tools\notice_da_demo.py",
    "tools\test_demo_app.py",
    "tools\test_demos.py",
    "tools\compare_deliveries.py",
    "tools\extract_corsair.py",
    "tools\index_atlas.py",
    "tools\measure_cads_orientation.py",
    "tools\prova_conjunto_mse.py",
    "tools\read_literature.py",
    "tools\repair_rtstruct.py",
    "tools\resegment.py",
    "tools\scan_literature.py"
)
foreach ($o in $ORFAOS) {
    $p = Join-Path $INST $o
    if (Test-Path -LiteralPath $p) {
        Remove-Item -LiteralPath $p -Force -ErrorAction SilentlyContinue
    }
}
$PASTAS_ORFAS = @("demo")
foreach ($o in $PASTAS_ORFAS) {
    $p = Join-Path $INST $o
    if (Test-Path -LiteralPath $p -PathType Container) {
        try {
            Remove-Item -LiteralPath $p -Recurse -Force -ErrorAction Stop
            Diga ("  a pasta " + $o + "\ saiu: o programa nao a usa mais")
        } catch {
            Diga ("  AVISO: nao consegui remover a pasta " + $o + "\ (" + $_.Exception.Message + ")")
        }
    }
}

Copy-Item -LiteralPath (Join-Path $PACOTE "entrega.txt") `
          -Destination (Join-Path $INST "entrega.txt") -Force
$reqPac = Join-Path $PACOTE "_requisitos.json"
if (Test-Path -LiteralPath $reqPac) {
    Copy-Item -LiteralPath $reqPac -Destination (Join-Path $INST "_requisitos.json") -Force
}
foreach ($nm in $DOCUMENTOS) {
    $o = Join-Path $PACOTE $nm
    if (Test-Path -LiteralPath $o -PathType Leaf) {
        $a = Join-Path $INST $nm
        $pa = Split-Path -Parent $a
        if ($pa -and -not (Test-Path -LiteralPath $pa)) {
            New-Item -ItemType Directory -Path $pa -Force | Out-Null
        }
        Copy-Item -LiteralPath $o -Destination $a -Force
    }
}

$RAIZ = Split-Path -Parent $INST
$PROJ = $PROJETO_NOVO
if (-not $PROJ) { $PROJ = Split-Path -Leaf $INST }
# GUARDA: regra unica do registro, a mesma do INSTALL.ps1 e do app: no PAI
# da pasta do programa, nunca dentro dela.
$REG = Join-Path $RAIZ "_instalados.json"
try {
    $j = [ordered]@{}
    $velha = $null
    if (Test-Path -LiteralPath $REG) {
        $lido = [System.IO.File]::ReadAllText($REG, [System.Text.Encoding]::UTF8) | ConvertFrom-Json
        foreach ($p in $lido.PSObject.Properties) {
            $j[$p.Name] = $p.Value
            if ($p.Name -eq $PROJ) { $velha = $p.Value }
        }
    }
    $nova = [ordered]@{}
    if ($velha) {
        $ondeVelha = ""
        try { if ($velha.caminho) { $ondeVelha = [string]$velha.caminho } } catch { }
        if ($ondeVelha -and ($ondeVelha.TrimEnd('\') -ine $INST.TrimEnd('\'))) {
            Diga ("  o registro dizia " + $PROJ + " em " + $ondeVelha + "; agora diz esta pasta")
        } else {
            foreach ($p in $velha.PSObject.Properties) { $nova[$p.Name] = $p.Value }
        }
    }
    $nova["versao"] = $VERSAO_NOVA
    $nova["caminho"] = $INST
    $nova["pasta"] = $INST
    $nova["data"] = (Get-Date -Format "yyyy-MM-dd HH:mm")
    $nova["como"] = "atualizacao de codigo (offline)"
    $j[$PROJ] = $nova
    [System.IO.File]::WriteAllText($REG, ($j | ConvertTo-Json -Depth 8),
                                   (New-Object System.Text.UTF8Encoding($false)))
    Diga ("  _instalados.json: " + $PROJ + " -> " + $VERSAO_NOVA + "  (" + $REG + ")")
    $regDentro = Join-Path $INST "_instalados.json"
    if (Test-Path -LiteralPath $regDentro -PathType Leaf) {
        $jd = [System.IO.File]::ReadAllText($regDentro, [System.Text.Encoding]::UTF8) | ConvertFrom-Json
        if ($jd.PSObject.Properties.Name -contains $PROJ) {
            $novoNome = $regDentro + ".antigo"
            if (Test-Path -LiteralPath $novoNome) {
                $novoNome = $regDentro + ".antigo_" + (Get-Date -Format "yyyyMMdd-HHmmss")
            }
            Move-Item -LiteralPath $regDentro -Destination $novoNome
            Diga ("  o registro antigo de dentro da pasta do programa virou " + (Split-Path -Leaf $novoNome))
            Diga ("  (ele nao e mais lido: o desta instalacao e " + $REG + ")")
        }
    }
} catch { Diga ("  AVISO: nao consegui atualizar o " + $REG + " (" + $_.Exception.Message + ")") }

Diga ""
Diga "  4/5  Atalhos: area de trabalho e menu Iniciar"
[void](CriarAtalhos $INST $RAIZ)
$icoNovo = Join-Path $INST "favicon.ico"
if (Test-Path -LiteralPath $icoNovo) {
    if ($env:RADAI_ATALHOS_NA_RAIZ) {
        $pastasLnk = @((Join-Path $RAIZ "_atalhos_desktop"),
                       (Join-Path $RAIZ "_atalhos_menu"))
    } else {
        $pastasLnk = @([Environment]::GetFolderPath("Desktop"),
                       (Join-Path ([Environment]::GetFolderPath("Programs")) "Radioterapia.AI"))
    }
    $refeitos = 0
    try {
        $ws = New-Object -ComObject WScript.Shell
        foreach ($pl in $pastasLnk) {
            if (-not (Test-Path -LiteralPath $pl)) { continue }
            foreach ($f in (Get-ChildItem -LiteralPath $pl -Filter "*.lnk" -File -ErrorAction SilentlyContinue)) {
                try {
                    $s = $ws.CreateShortcut($f.FullName)
                    $t = [string]$s.TargetPath
                    if (-not $t) { continue }
                    if (-not $t.StartsWith($INST.TrimEnd('\') + '\',
                            [System.StringComparison]::OrdinalIgnoreCase)) { continue }
                    $s.IconLocation = ($icoNovo + ',0')
                    $s.Save()
                    $refeitos++
                    Diga ("  icone do atalho refeito: " + $f.FullName)
                } catch {
                    Diga ("  AVISO: nao consegui refazer o icone de " + $f.Name +
                          " (" + $_.Exception.Message + ")")
                }
            }
        }
    } catch {
        Diga ("  AVISO: nao consegui abrir os atalhos (" + $_.Exception.Message + ")")
    }
    if ($refeitos -eq 0) {
        Diga "  (nenhum atalho desta instalacao para refazer o icone)"
    }
}

Diga ""
$script:CodigoCompleto = $true
if ($Reabrir) {
    Diga "  5/5  Iniciando a versao nova do Local Suite..."
    if (-not (ReabrirOApp)) { Pare ("O codigo foi atualizado, mas nao consegui iniciar o app: " + $script:MotivoReabrir) }
    if (-not (AguardarPainelNovo (PortaDaInstalacao $INST) $VERSAO_NOVA)) {
        Pare ("O codigo foi atualizado, mas a reabertura nao foi confirmada: " + $script:MotivoReabrir)
    }
    Diga ("  Painel da v" + $VERSAO_NOVA + " confirmado em um processo novo.")
}
Diga "============================================================"
Diga ("  ATUALIZADO. versao " + $VERSAO_VELHA + " -> " + $VERSAO_NOVA)
Diga "============================================================"
Diga ""
if ($Reabrir) {
    Diga "  O app reabre sozinho, com a sua configuracao."
} else {
    Diga "  Abra pelo atalho da area de trabalho, como sempre."
}
Diga ""
Sair 0
