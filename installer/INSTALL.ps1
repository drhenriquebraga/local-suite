$ErrorActionPreference = "Stop"

$PRESERVAR = @(
    "radai_watcher.config",
    "_dados.txt",
    "_bundle.txt",
    "calibracao",
    "registro",
    "radai_status.json",
    "nomes_proprios.json",
    "protocolos_proprios.json"
)
$PRESERVAR_PADRAO = @("*.log")

$ESSENCIAIS = @(
    "python\python.exe",
    "radai_watcher.py",
    "engine.py",
    "radai_geom.py",
    "RADIOTERAPIA_AI_LOCAL_SUITE.cmd",
    "launchers\start_watcher.cmd",
    "ts_weights"
)

if (-not (Get-Command T -ErrorAction SilentlyContinue)) {
    function T { param([AllowEmptyString()][string]$Texto) return $Texto }
}
function Diga($txt)  { Write-Host (T $txt) }
function Anote($txt) { try { Add-Content -LiteralPath $script:LOG -Value $txt -Encoding UTF8 } catch { } }
function Passo($txt) { Diga ""; Diga ("-- " + $txt); Anote ("-- " + $txt) }

function Pare($txt) {
    Diga ""
    Diga "============================================================"
    Diga "  A INSTALACAO PAROU"
    Diga ""
    foreach ($l in ($txt -split "`n")) { Diga ("  " + $l) }
    Diga ""
    Diga ("  Log: " + $script:LOG)
    Diga "============================================================"
    Anote ("ERRO: " + $txt)
    exit 1
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

function ProcessoDaPasta($id, $pasta) {
    # GUARDA: so python.exe ou pythonw.exe cujo executavel mora na pasta
    # instalada; outro Python da maquina nunca e encerrado.
    $p = $null
    try { $p = Get-CimInstance Win32_Process -Filter ("ProcessId=" + [int]$id) -ErrorAction Stop } catch { $p = $null }
    if (-not $p) { return $false }
    $nome = ([string]$p.Name).ToLower()
    if ($nome -ne "python.exe" -and $nome -ne "pythonw.exe") { return $false }
    $exe = [string]$p.ExecutablePath
    if (-not $exe) {
        try { $exe = [string](Get-Process -Id ([int]$id) -ErrorAction Stop).Path } catch { $exe = "" }
    }
    if (-not $exe) { return $false }
    return $exe.StartsWith((_Prefixo $pasta), [System.StringComparison]::OrdinalIgnoreCase)
}

function EstadoDoMotor($porta) {
    if (-not $env:LOCALAPPDATA) { return "" }
    return (Join-Path (Join-Path $env:LOCALAPPDATA "RADIOTERAPIA_AI") ("motor_" + $porta + ".json"))
}

function ProcessosDoApp($pasta, $porta) {
    $ids = @()
    $est = EstadoDoMotor $porta
    if ($est -and (Test-Path -LiteralPath $est -PathType Leaf)) {
        try {
            $j = [System.IO.File]::ReadAllText($est, [System.Text.Encoding]::UTF8) | ConvertFrom-Json
            $idj = 0
            try { $idj = [int]$j.pid } catch { $idj = 0 }
            if ([string]$j.estado -eq "rodando" -and $idj -gt 0) {
                if (ProcessoDaPasta $idj $pasta) { $ids += $idj }
                elseif (Get-Process -Id $idj -ErrorAction SilentlyContinue) {
                    Diga ("  o PID " + $idj + " do estado do motor nao e o Python desta pasta: nao mexo nele")
                }
            }
        } catch { }
    }
    $pfx = _Prefixo $pasta
    try {
        foreach ($p in @(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" -ErrorAction Stop)) {
            $exe = [string]$p.ExecutablePath
            if ($exe -and $exe.StartsWith($pfx, [System.StringComparison]::OrdinalIgnoreCase)) {
                if ($ids -notcontains [int]$p.ProcessId) { $ids += [int]$p.ProcessId }
            }
        }
    } catch { }
    return $ids
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
        if ($agora.Count -eq 0) { break }
        foreach ($i in $agora) {
            if (-not (ProcessoDaPasta $i $pasta)) { continue }
            try {
                Stop-Process -Id $i -Force -ErrorAction Stop
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
    if ($resto.Count -gt 0) {
        $script:PidsQueFicaram = $resto
        Diga ("  continua aberto: PID " + ($resto -join ", "))
        return "resistiu"
    }
    Diga ("  app encerrado (PID " + ($ids -join ", ") + "); sigo")
    return "encerrado"
}

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

$AQUI = $env:RADAI_PASTA_PACOTE
if (-not $AQUI) {
    try { if ($MyInvocation.MyCommand.Path) { $AQUI = Split-Path -Parent $MyInvocation.MyCommand.Path } } catch { }
}
if (-not $AQUI) { $AQUI = $PSScriptRoot }
if (-not $AQUI) { $AQUI = (Get-Location).Path }
$AQUI = $AQUI.TrimEnd('\')
# GUARDA: no lugar (instalacao direta), a carga JA e o destino; nada se copia e nada se apaga.
$NO_LUGAR = ''
if ($env:RADAI_INSTALAR_NO_LUGAR) { $NO_LUGAR = $env:RADAI_INSTALAR_NO_LUGAR.Trim().TrimEnd('\') }

try {
    $mod = Join-Path $AQUI 'languages.ps1'
    if (Test-Path -LiteralPath $mod) {
        . $mod
        [void](Carregar-Idiomas $AQUI)
        $idi = ''
        if ($env:RADAI_IDIOMA) {
            $idi = $env:RADAI_IDIOMA
        } else {
            $f = Join-Path $AQUI 'idioma.txt'
            if ($NO_LUGAR) { $f = Join-Path $NO_LUGAR 'idioma.txt' }
            if (Test-Path -LiteralPath $f) {
                $idi = (Get-Content -LiteralPath $f -Raw -Encoding UTF8).Trim()
            }
        }
        if ($idi) { Idioma-Definir $idi }
    }
} catch { }
$script:LOG = Join-Path $AQUI "INSTALL_LOG.txt"
if ($NO_LUGAR) { $script:LOG = Join-Path $NO_LUGAR "INSTALL_LOG.txt" }
Set-Content -LiteralPath $script:LOG -Value ("instalar " + (Get-Date -Format "dd/MM/yyyy HH:mm:ss")) -Encoding UTF8
Anote ("pasta: " + $AQUI)

$folha = Split-Path -Leaf $AQUI
if ($folha -match '^Temp\d+_') {
    Pare ("Voce esta rodando de dentro do arquivo .zip.`n" +
          "O Windows extraiu so este arquivo para uma pasta temporaria,`n" +
          "e o resto do pacote nao veio junto.`n`n" +
          "O QUE FAZER: feche esta janela. Clique com o botao direito no`n" +
          ".zip, escolha 'Extrair tudo...', e so entao rode o INSTALL.cmd`n" +
          "de dentro da pasta extraida.")
}

Passo "Lendo o entrega.txt"
$arqEntrega = Join-Path $AQUI "entrega.txt"
if ($NO_LUGAR) { $arqEntrega = Join-Path $NO_LUGAR "entrega.txt" }
if (-not (Test-Path -LiteralPath $arqEntrega)) {
    Pare ("Nao achei o entrega.txt nesta pasta:`n  " + $AQUI + "`n`n" +
          "Ele diz qual projeto e qual versao este pacote instala.`n" +
          "Provavelmente o .zip foi extraido pela metade.")
}
$campos = @{}
foreach ($linha in [System.IO.File]::ReadAllLines($arqEntrega, [System.Text.Encoding]::UTF8)) {
    $l = $linha.Trim()
    if ($l -eq "" -or $l.StartsWith("#") -or (-not $l.Contains("="))) { continue }
    $i = $l.IndexOf("=")
    $campos[$l.Substring(0, $i).Trim().ToUpper()] = $l.Substring($i + 1).Trim()
}
$PROJETO = $campos["PROJETO"]
$VERSAO  = $campos["VERSAO"]
if (-not $PROJETO) { Pare "O entrega.txt nao tem a linha PROJETO=." }
if (-not $VERSAO)  { Pare "O entrega.txt nao tem a linha VERSAO=." }
Diga ("   projeto: " + $PROJETO + "   versao: " + $VERSAO)
Anote ("projeto=" + $PROJETO + " versao=" + $VERSAO)

Passo "Conferindo o conteudo do pacote"
$CARGA = Join-Path $AQUI $PROJETO
if ($NO_LUGAR) { $CARGA = $NO_LUGAR }
if (-not (Test-Path -LiteralPath $CARGA)) {
    Pare ("Nao achei a pasta '" + $PROJETO + "' aqui dentro:`n  " + $AQUI + "`n`n" +
          "Ela carrega o programa. Extraia o .zip INTEIRO antes de instalar.")
}
$faltando = @()
foreach ($e in $ESSENCIAIS) {
    if (-not (Test-Path -LiteralPath (Join-Path $CARGA $e))) { $faltando += $e }
}
if ($faltando.Count -gt 0) {
    Pare ("O pacote esta incompleto. Nao achei:`n  " + ($faltando -join "`n  ") + "`n`n" +
          "Isso costuma ser download interrompido ou extracao pela metade.`n" +
          "Baixe de novo e extraia o .zip inteiro.")
}
$n = (Get-ChildItem -LiteralPath $CARGA -Recurse -File -ErrorAction SilentlyContinue).Count
Diga ("   " + $n + " arquivos, tudo que e essencial esta presente")

Passo "Licencas aceitas na preparacao"
$ARQ_LICENCAS = Join-Path $AQUI 'LICENCAS_ACEITAS.txt'
if ($NO_LUGAR) { $ARQ_LICENCAS = Join-Path $NO_LUGAR 'LICENCAS_ACEITAS.txt' }
if (Test-Path -LiteralPath $ARQ_LICENCAS) {
    $txtLic = [System.IO.File]::ReadAllText($ARQ_LICENCAS, [System.Text.Encoding]::UTF8)

    Write-Host ''
    Write-Host '   ============================================================'
    Write-Host '    LICENCAS DOS COMPONENTES DESTE PACOTE'
    Write-Host '   ============================================================'
    foreach ($l in ($txtLic -split "`r`n")) {
        if ($l.Trim()) { Write-Host ('   ' + $l) } else { Write-Host '' }
    }
    Write-Host '   ============================================================'
    Write-Host ''

    if ($txtLic -match 'RESTRICAO DE USO') {
        Write-Host '   ATENCAO: este pacote leva um componente de USO NAO COMERCIAL.'
        Write-Host '   NVIDIA License 3.3: pesquisa ou avaliacao, apenas. Isso e mais'
        Write-Host '   estreito que "sem fins lucrativos" -- servico publico em'
        Write-Host '   atendimento de rotina NAO esta coberto por ser publico.'
        Write-Host ''
    }

    $r = $null
    $viaAmbiente = $false
    if ($env:RADAI_LICENCAS_ACEITAS) {
        $r = $env:RADAI_LICENCAS_ACEITAS
        $viaAmbiente = $true
        Diga '   aceite declarado por RADAI_LICENCAS_ACEITAS (instalacao automatizada)'
    } else {
        try {
            $r = Read-Host '   Voce leu as licencas acima e concorda em usar este pacote nesta estacao? (S/N)'
        } catch {
            Pare ("Nao ha console para confirmar as licencas, e este pacote exige" + [char]10 +
                  "confirmacao de quem instala." + [char]10 + [char]10 +
                  "Se voce esta automatizando a instalacao, declare o aceite antes:" + [char]10 +
                  "   set RADAI_LICENCAS_ACEITAS=S" + [char]10 + [char]10 +
                  "Isso fica registrado no log como aceite AUTOMATIZADO, e nao como" + [char]10 +
                  "alguem tendo lido as licencas nesta estacao.")
        }
    }
    if ($r -notmatch '^[SsYy]') {
        Pare ("Instalacao cancelada: as licencas nao foram aceitas nesta estacao." + [char]10 + [char]10 +
              "Nada foi copiado. Se o componente nao comercial for o impedimento," + [char]10 +
              "prepare um pacote novo SEM ele -- o preparador tem essa opcao, e o" + [char]10 +
              "TotalSegmentator faz o fluxo principal sozinho.")
    }
    Anote ('licencas_reexibidas=' + $(if ($viaAmbiente) { 'automatizado' } else { 'confirmado_no_console' }))
    Diga '   licencas aceitas nesta estacao'
} else {
    Diga '   este pacote nao traz LICENCAS_ACEITAS.txt.'
    Diga '   Ou foi montado direto pelo empacotador (sem passar pelo preparador),'
    Diga '   ou e anterior a 19/08/2026. As licencas estao no NOTICE, ao lado.'
    Anote 'licencas_reexibidas=arquivo_ausente'
}


Passo "Escolhendo o destino"
$PADRAO_RAIZ = "C:\RADIOTERAPIA_AI"

$PRECISA = 0
if (-not $NO_LUGAR) { try {
    $PRECISA = [int64](((Get-ChildItem -LiteralPath $CARGA -Recurse -File `
                          -ErrorAction SilentlyContinue) |
                        Measure-Object -Property Length -Sum).Sum * 1.10)
} catch { $PRECISA = 0 } }

function _Livre($caminho) {
    try {
        $q = [System.IO.Path]::GetPathRoot($caminho)
        if (-not $q) { return -1 }
        return (New-Object System.IO.DriveInfo($q)).AvailableFreeSpace
    } catch { return -1 }
}
function _GB($b) { if ($b -lt 0) { return "?" } return ("{0:N1} GB" -f ($b / 1GB)) }

$RAIZ = $env:RADAI_RAIZ_INSTALACAO
if ($NO_LUGAR) {
    $RAIZ = Split-Path -Parent $NO_LUGAR
    Diga "   instalacao direta: o programa ja esta na pasta final"
} elseif ($RAIZ) {
    Diga "   (raiz vinda de RADAI_RAIZ_INSTALACAO)"
} else {
    if ($PRECISA -gt 0) { Diga ("   o pacote ocupa " + (_GB $PRECISA) + " instalado") }

    $unidades = @()
    foreach ($d in [System.IO.DriveInfo]::GetDrives()) {
        try {
            if (-not $d.IsReady) { continue }
            if ($d.DriveType -ne [System.IO.DriveType]::Fixed) { continue }
            $unidades += [pscustomobject]@{
                Raiz  = (Join-Path $d.Name "RADIOTERAPIA_AI")
                Livre = $d.AvailableFreeSpace
                Cabe  = ($PRECISA -le 0 -or $d.AvailableFreeSpace -gt $PRECISA)
            }
        } catch { }
    }
    $sugestao = $null
    $pad = $unidades | Where-Object { $_.Raiz -eq $PADRAO_RAIZ -and $_.Cabe }
    if ($pad) { $sugestao = $PADRAO_RAIZ }
    else {
        $m = $unidades | Where-Object { $_.Cabe } |
             Sort-Object Livre -Descending | Select-Object -First 1
        if ($m) { $sugestao = $m.Raiz }
    }
    if (-not $sugestao) { $sugestao = $PADRAO_RAIZ }

    foreach ($u in $unidades) {
        $marca = "   "
        if ($u.Raiz -eq $sugestao) { $marca = " > " }
        $cabe = ""
        if (-not $u.Cabe) { $cabe = "   (nao cabe)" }
        Diga ($marca + $u.Raiz + "   livre: " + (_GB $u.Livre) + $cabe)
    }

    if ($env:RADAI_DESTINO_AUTO) {
        $RAIZ = $sugestao
        Diga "   escolhido automaticamente por RADAI_DESTINO_AUTO"
    } else {
        try {
            $r = Read-Host ("   Onde instalar? ENTER para " + $sugestao)
        } catch {
            $r = ""
            Diga "   (sem console: fica o sugerido)"
        }
        if ($r) { $r = $r.Trim().Trim([char]34) }
        if (-not $r) { $RAIZ = $sugestao }
        elseif ($r.Length -le 3 -and $r -match "^[A-Za-z]:?\\?$") {
            $RAIZ = Join-Path ($r.Substring(0,1) + ":\") "RADIOTERAPIA_AI"
        } else { $RAIZ = $r }
    }
}

$livre = _Livre $RAIZ
if ((-not $NO_LUGAR) -and $PRECISA -gt 0 -and $livre -ge 0 -and $livre -lt $PRECISA) {
    Diga ""
    Diga ("   AVISO: " + $RAIZ + " tem " + (_GB $livre) + " livres e o pacote")
    Diga ("   ocupa " + (_GB $PRECISA) + ". A copia pode parar no meio.")
    Diga ""
    Anote ("espaco insuficiente: livre=" + $livre + " precisa=" + $PRECISA)
}
if (-not $NO_LUGAR) {
  try {
    if (-not (Test-Path -LiteralPath $RAIZ)) { New-Item -ItemType Directory -Path $RAIZ -Force | Out-Null }
    $teste = Join-Path $RAIZ ("_escrita_" + $PID + ".tmp")
    [System.IO.File]::WriteAllText($teste, "x")
    Remove-Item -LiteralPath $teste -Force
  } catch {
    $RAIZ = Join-Path $env:LOCALAPPDATA "RADIOTERAPIA_AI"
    Diga ("   AVISO: sem permissao de escrita em " + $RAIZ + ".")
    Diga ("   Usando a pasta do usuario: " + $RAIZ)
    Anote "fallback para LOCALAPPDATA"
    if (-not (Test-Path -LiteralPath $RAIZ)) { New-Item -ItemType Directory -Path $RAIZ -Force | Out-Null }
  }
}
$folha = Split-Path -Leaf $RAIZ
if ($NO_LUGAR) {
    $DESTINO = $NO_LUGAR
    Anote ("destino=no lugar")
} elseif ($folha -and ($folha -eq $PROJETO)) {
    $DESTINO = $RAIZ
    Diga ("   a raiz ja termina em '" + $PROJETO + "' -- instalando nela mesma")
    Anote ("destino=raiz (a folha ja e o projeto)")
} else {
    $DESTINO = Join-Path $RAIZ $PROJETO
}
Diga ("   " + $DESTINO)
Anote ("destino=" + $DESTINO)

Passo "Procurando instalacao anterior"
# GUARDA: regra unica do registro: no PAI da pasta do programa, nunca dentro dela.
$REGISTRO = Join-Path (Split-Path -Parent $DESTINO) "_instalados.json"
$anterior = $null
if (Test-Path -LiteralPath $REGISTRO) {
    try {
        $j = [System.IO.File]::ReadAllText($REGISTRO, [System.Text.Encoding]::UTF8) | ConvertFrom-Json
        if ($j.PSObject.Properties.Name -contains $PROJETO) { $anterior = $j.$PROJETO.versao }
    } catch { Anote "registro ilegivel; sera refeito" }
}
if ((-not $anterior) -and (Test-Path -LiteralPath $DESTINO)) { $anterior = "(desconhecida)" }

if ($anterior) {
    Diga ("   ja instalado: versao " + $anterior + "  ->  instalando " + $VERSAO)
    Anote ("anterior=" + $anterior)
    $cmp = $null
    try { $cmp = ([version]$VERSAO).CompareTo([version]$anterior) } catch { }
    if ((-not $NO_LUGAR) -and $cmp -ne $null -and $cmp -lt 0) {
        Diga ""
        Diga ("   ATENCAO: a versao instalada (" + $anterior + ") e MAIS NOVA que a")
        Diga ("   deste pacote (" + $VERSAO + "). Instalar vai retroceder a estacao.")
        Diga ""
        $r = ""
        try { $r = Read-Host "   Continuar mesmo assim? (digite SIM para continuar)" }
        catch { Diga "   (sem console para perguntar)" }
        if ($r -ne "SIM") { Diga ""; Diga "   Cancelado. Nada foi alterado."; Anote "downgrade recusado"; exit 2 }
    } elseif ($cmp -ne $null -and $cmp -eq 0) {
        Diga "   mesma versao: os arquivos do programa serao reescritos."
    }
} else {
    Diga "   nenhuma — instalacao nova"
}

$guardados = @()
if (Test-Path -LiteralPath $DESTINO) {
    Passo "Dado local que sera preservado"
    foreach ($nome in $PRESERVAR) {
        if (Test-Path -LiteralPath (Join-Path $DESTINO $nome)) { $guardados += $nome }
    }
    foreach ($padrao in $PRESERVAR_PADRAO) {
        foreach ($f in (Get-ChildItem -LiteralPath $DESTINO -Filter $padrao -File -ErrorAction SilentlyContinue)) {
            $guardados += $f.Name
        }
    }
    if ($guardados.Count -gt 0) {
        foreach ($g in $guardados) { Diga ("   mantido: " + $g) }
    } else {
        Diga "   nada a preservar (instalacao anterior sem dado local)"
    }
    Anote ("preservados: " + ($guardados -join ", "))
}

if ((-not $NO_LUGAR) -and (Test-Path -LiteralPath (Join-Path $DESTINO "radai_watcher.py"))) {
    Passo "Conferindo se o app esta aberto nesta pasta"
    # GUARDA: copiar por cima do app aberto prende arquivo e deixa codigo velho
    # em memoria; a regra e a do atualizador, que so encerra o Python da pasta.
    while ($true) {
        $enc = EncerrarOApp $DESTINO
        $preso = ($enc -eq "resistiu")
        if (-not $preso) {
            $pE = PortaDaInstalacao $DESTINO
            if (PortaViva $pE) {
                if (EONossoPainel $pE) {
                    Diga ("  a porta " + $pE + " ainda responde o painel do Local Suite, de um")
                    Diga "  processo que nao e desta pasta ou que nao consegui conferir"
                    $preso = $true
                } else {
                    Diga ("  a porta " + $pE + " esta com outro programa, que nao e o app: nao mexo nele")
                }
            }
        }
        if (-not $preso) {
            if ($enc -eq "nada") { Diga "  o app nao esta aberto nesta pasta" }
            Anote ("app aberto: " + $enc)
            break
        }
        Anote "app aberto: nao consegui encerrar"
        Diga ""
        Diga "  Nao consegui encerrar o app aberto nesta pasta. Feche-o pela"
        Diga "  engrenagem (Fechar, Fechar tudo) ou pelo Gerenciador de Tarefas."
        $c = $null
        try { $c = Read-Host "  Tentar de novo? (S/N)" } catch { $c = $null }
        if ($null -eq $c) {
            Pare ("O app esta aberto nesta pasta e nao consegui encerra-lo:`n  " + $DESTINO + "`n`n" +
                  "Nada foi copiado. Feche-o pela engrenagem (Fechar, Fechar tudo)`n" +
                  "ou pelo Gerenciador de Tarefas e rode o INSTALL.cmd de novo.")
        }
        if ($c.Trim().ToUpper() -ne "S") {
            Diga ""
            Diga "   Cancelado. Nada foi alterado."
            Anote "app aberto: cancelado"
            exit 2
        }
    }
}

Passo "Copiando o programa"
if ($NO_LUGAR) {
    Diga "   instalacao direta: o programa ja esta na pasta final, nada a copiar"
    Anote "copia=nenhuma (no lugar)"
} else {
Diga "   sao varios GB. Pode demorar. NAO feche esta janela."
if (-not (Test-Path -LiteralPath $DESTINO)) { New-Item -ItemType Directory -Path $DESTINO -Force | Out-Null }
$rcLog = Join-Path $AQUI "INSTALAR_COPIA_LOG.txt"
$rcArgs = @($CARGA, $DESTINO, "/E", "/R:2", "/W:2", "/NFL", "/NDL", "/NP")
$proc = Start-Process -FilePath "robocopy.exe" -ArgumentList $rcArgs `
        -RedirectStandardOutput $rcLog -NoNewWindow -PassThru
try { $null = $proc.Handle } catch { }
$t0 = Get-Date
while (-not $proc.HasExited) {
    Start-Sleep -Seconds 15
    if ($proc.HasExited) { break }
    $gb = 0.0
    try {
        $soma = (Get-ChildItem -LiteralPath $DESTINO -Recurse -File `
                 -ErrorAction SilentlyContinue |
                 Measure-Object -Property Length -Sum).Sum
        if ($soma) { $gb = $soma / 1GB }
    } catch { }
    $seg = [int]((Get-Date) - $t0).TotalSeconds
    Diga ("   copiando... {0:N1} GB  ({1}m{2:00}s)" -f $gb,
          [int][math]::Floor($seg / 60), ($seg % 60))
}
$proc.WaitForExit()
$rc = $null
try { $rc = $proc.ExitCode } catch { }
if ($null -eq $rc) {
    Diga "   AVISO: o robocopy nao devolveu codigo de saida."
    Diga "   A conferencia dos arquivos, abaixo, e o que vale aqui."
    Anote "robocopy sem ExitCode"
} elseif ($rc -ge 8) {
    Pare ("A copia falhou (robocopy " + $rc + ").`n" +
          "Detalhe em: " + $rcLog + "`n`n" +
          "Causas comuns: disco cheio, antivirus segurando arquivo,`n" +
          "ou o pendrive removido no meio da copia.")
}
if ($null -eq $rc) { Diga "   copia terminada (sem codigo do robocopy)" }
else { Diga ("   copia concluida (robocopy " + $rc + ")") }
Anote ("robocopy=" + $rc)
}

foreach ($pc in (Get-ChildItem -LiteralPath $DESTINO -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue)) {
    try { Remove-Item -LiteralPath $pc.FullName -Recurse -Force } catch { }
}

$ORFAOS = @(
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
    $po = Join-Path $DESTINO $o
    if (Test-Path -LiteralPath $po) {
        try { Remove-Item -LiteralPath $po -Force } catch { }
    }
}
$PASTAS_ORFAS = @("demo")
foreach ($o in $PASTAS_ORFAS) {
    $po = Join-Path $DESTINO $o
    if (Test-Path -LiteralPath $po -PathType Container) {
        try {
            Remove-Item -LiteralPath $po -Recurse -Force
            Diga ("   a pasta " + $o + "\ saiu: o programa nao a usa mais")
            Anote ("pasta orfa removida: " + $o)
        } catch {
            Diga ("   AVISO: nao consegui remover a pasta " + $o + "\ (" + $_.Exception.Message + ")")
        }
    }
}

Passo "Conferindo a instalacao"
$faltando = @()
foreach ($e in $ESSENCIAIS) {
    if (-not (Test-Path -LiteralPath (Join-Path $DESTINO $e))) { $faltando += $e }
}
if ($faltando.Count -gt 0) {
    Pare ("A copia terminou mas faltam arquivos no destino:`n  " + ($faltando -join "`n  ") + "`n`n" +
          "A instalacao NAO esta utilizavel. Veja " + $rcLog)
}
foreach ($g in $guardados) {
    if (-not (Test-Path -LiteralPath (Join-Path $DESTINO $g))) {
        Pare ("O dado local '" + $g + "' sumiu durante a instalacao.`n" +
              "Isto e um defeito do instalador — nao continue.`n" +
              "Avise quem administra esta instalacao e guarde o log.")
    }
}
Diga ("   " + $ESSENCIAIS.Count + " arquivos essenciais no lugar")
if ($guardados.Count -gt 0) { Diga ("   " + $guardados.Count + " item(ns) de dado local intactos") }

Passo "Atalhos: area de trabalho e menu Iniciar"
[void](CriarAtalhos $DESTINO $RAIZ)

Passo "Registrando em _instalados.json"
$ok = $false
for ($tentativa = 1; $tentativa -le 5; $tentativa++) {
    try {
        $dados = New-Object System.Collections.Specialized.OrderedDictionary
        if (Test-Path -LiteralPath $REGISTRO) {
            try {
                $j = [System.IO.File]::ReadAllText($REGISTRO, [System.Text.Encoding]::UTF8) | ConvertFrom-Json
                foreach ($prop in $j.PSObject.Properties) { $dados[$prop.Name] = $prop.Value }
            } catch {
                $bak = $REGISTRO + ".corrompido"
                Copy-Item -LiteralPath $REGISTRO -Destination $bak -Force
                Diga ("   AVISO: o registro estava ilegivel. Copia em " + $bak)
                Anote "registro corrompido; recomecando"
            }
        }
        $dados[$PROJETO] = [pscustomobject]@{
            versao  = $VERSAO
            data    = (Get-Date -Format "yyyy-MM-dd")
            caminho = $DESTINO
        }
        $txt = ($dados | ConvertTo-Json -Depth 5)
        [System.IO.File]::WriteAllText($REGISTRO, $txt, (New-Object System.Text.UTF8Encoding($false)))
        $ok = $true
        break
    } catch {
        Start-Sleep -Milliseconds (200 * $tentativa)
    }
}
if ($ok) {
    Diga ("   " + $PROJETO + " " + $VERSAO + " registrado em " + $REGISTRO)
} else {
    Diga "   AVISO: nao consegui escrever o registro compartilhado."
    Diga "   O programa funciona; so o diagnostico remoto fica sem esta entrada."
    Anote "registro nao gravado"
}
$regDentro = Join-Path $DESTINO "_instalados.json"
if ($ok -and (Test-Path -LiteralPath $regDentro -PathType Leaf)) {
    try {
        $jd = [System.IO.File]::ReadAllText($regDentro, [System.Text.Encoding]::UTF8) | ConvertFrom-Json
        if ($jd.PSObject.Properties.Name -contains $PROJETO) {
            $novoNome = $regDentro + ".antigo"
            if (Test-Path -LiteralPath $novoNome) {
                $novoNome = $regDentro + ".antigo_" + (Get-Date -Format "yyyyMMdd-HHmmss")
            }
            Move-Item -LiteralPath $regDentro -Destination $novoNome
            Diga ("   o registro antigo de dentro da pasta do programa virou " + (Split-Path -Leaf $novoNome))
            Diga ("   (ele nao e mais lido: o desta instalacao e " + $REGISTRO + ")")
            Anote ("registro de dentro renomeado: " + $novoNome)
        }
    } catch {
        Diga ("   AVISO: nao consegui renomear o registro antigo " + $regDentro)
        Anote ("registro de dentro: " + $_.Exception.Message)
    }
}

Diga ""
Diga "============================================================"
Diga ("  PRONTO. " + $PROJETO + " " + $VERSAO + " instalado em:")
Diga ("  " + $DESTINO)
Diga ""
Diga "  PROXIMOS PASSOS:"
Diga "    1) Abra a suite pelo atalho 'Radioterapia.ai Local Suite' da"
Diga "       area de trabalho. Na primeira vez ela pede o aceite."
Diga "    2) Em Configuracoes, Diagnosticos e Registros, clique em"
Diga "       Diagnosticar: tem de dar 0 faltando."
Diga "    3) Na primeira abertura, depois do aceite, o programa pede a"
Diga "       pasta favorita, que e opcional. A pasta que o turno varre se"
Diga "       escolhe no ContourLab, em Rodar agora, Incluir Overnight Run:"
Diga "       sem ela o vigia nao varre nada. Os aneis saem no padrao"
Diga "       Eclipse / Monaco; para Xio / Focal, Configuracoes, Geral."
Diga ""
Diga "  As estruturas entram no TPS como SUGESTAO NAO APROVADA"
Diga "  (sufixo _ai). Revisar e aprovar continua sendo ato medico."
Diga "============================================================"
Anote "OK"
exit 0
