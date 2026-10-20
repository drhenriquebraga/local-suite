param([string]$Destino = "", [string]$Python = "", [switch]$SemPerguntar,
      [switch]$SoEncerrar)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$AQUI = $PSScriptRoot
if (-not $AQUI) { $AQUI = Split-Path -Parent $MyInvocation.MyCommand.Path }
$PACOTE = Split-Path -Parent $AQUI
if (-not (Test-Path -LiteralPath (Join-Path $PACOTE "app"))) { $PACOTE = $AQUI }

function Diga($t) { Write-Host $t }
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
function PareCom($t, $codigo) {
    Diga ""
    Diga "============================================================"
    Diga "  A ATUALIZACAO NAO ACONTECEU"
    Diga ""
    foreach ($l in ($t -split "`n")) { Diga ("  " + $l) }
    Diga "============================================================"
    Diga ""
    exit $codigo
}
function Pare($t) { PareCom $t 1 }

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
    exit 3
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
Diga "  Copiando..."
function Aplicar($de, $para, $so) {
    if (-not (Test-Path -LiteralPath $para)) {
        New-Item -ItemType Directory -Path $para -Force | Out-Null
    }
    foreach ($it in (_Relativos $de $so)) {
        $alvo = Join-Path $para $it.rel
        $pasta = Split-Path -Parent $alvo
        if ($pasta -and -not (Test-Path -LiteralPath $pasta)) {
            New-Item -ItemType Directory -Path $pasta -Force | Out-Null
        }
        Copy-Item -LiteralPath $it.f.FullName -Destination $alvo -Force
    }
}
Aplicar (Join-Path $PACOTE "app") $INST $EXT_APP
Aplicar (Join-Path $PACOTE "tools") (Join-Path $INST "tools") $EXT_TOOLS

foreach ($pc in (Get-ChildItem -LiteralPath $INST -Recurse -Directory `
                 -Filter "__pycache__" -ErrorAction SilentlyContinue)) {
    Remove-Item -LiteralPath $pc.FullName -Recurse -Force -ErrorAction SilentlyContinue
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
Diga "============================================================"
Diga ("  ATUALIZADO. versao " + $VERSAO_VELHA + " -> " + $VERSAO_NOVA)
Diga "============================================================"
Diga ""
Diga "  Abra pelo atalho da area de trabalho, como sempre."
Diga ""
exit 0
